# -*- coding: utf-8 -*-
"""
マニピュレータ (ホバーと描画)。

段階 3: マウスの下の面を強調する。まだ何も押せない。
段階 4: 面の角 / 辺から、マウスに最も近い頂点 / エッジを拾って強調する (core.picking)。
        拾うもの (頂点 / エッジ) はコンテキストが setPickMode で渡す (設定 pickMode)。
段階 6: drawUI は「描画の一覧 (core.draw_list) を作って tool.drawing.render に渡す」だけ。
        色・太さ・手前に出す度合いは core.draw_list.THEME。
段階 7: スタートからマウスの下までのパスのプレビュー (黄) とスタート (緑) を描く。
        プレビューは拾ったものが変わったときと、スタートが変わったとき (updatePreview) に引く。
段階 8: 確定した区間 (未実行はマゼンタ) と、区間の両端の印を描く (いちばん下)。
段階 10: ビューの下の中央にボタン (core.actions の操作の表・core.panel の配置) を描く。
        ボタンは押せる部品 (kSelectable。ScreenPlane で 3D に戻した四角)。押下はマニピュレータの
        doPress に届き (glActiveName でどのボタンか)、離したときに同じボタンの上なら実行する
        (押したまま外へ動かせばやめられる)。ボタンの上ではメッシュを拾わない。
段階 13: 描く前 (preDrawUI) とマウスの移動 (doMove) で、コンテキストの syncMesh (setSync で渡す) を
        呼んで外部の変更を取り込む (変わっていればコンテキストが clearPick で拾ったものを捨てる)。
段階 16: モード (setMode)。選択のモードではパスのプレビューを描かず (クリックは Maya の選択)、
        ボタンはそのモードで見えるものだけ (core.actions.visible_actions)。
段階 19: 輪切りのモードでは拾わず、コンテキストが探したループ (setRingPreview) を描く。
段階 17: 対称がオンなら、パスのプレビュー・スタート・拾ったものの反対側をうすく描く (確定した区間は
        区間が反対側のエッジも持つので、そのまま両側が描かれる)。対応表はコンテキストの mirrorFor
        (setMirrorProvider で渡す)。プレビューが変わったときに作り直す (描くたびには引かない)。
段階 16c: 選択のモードのホバー。マウスの下のエッジ (拾うものによらずエッジ) から、ダブルクリックで
        選ばれるループ (scene.mesh.MeshModel.edgeLoop) をプレビューの色で描く。
段階 14: 複数のメッシュ。対象 (scene.targets.TargetSet) のいちばん手前の面で拾い、どのメッシュで拾ったか
        (pickTarget) も持つ。区間は全メッシュの分を描く。スタートとプレビューは、スタートを置いた
        メッシュだけ (コンテキストの start_state が (メッシュ, セッション) を返す)。

仕組み:
- マニピュレータは MPxManipulatorNode を継承した「ノード」。プラグインが registerNode で
  kManipulatorNode として登録し、コンテキストが newManipulator(ノードの型の名前) で作る。
  newManipulator は (Python のインスタンス, MObject) を返す。インスタンスはコンテキストが
  持って値を渡し (setModel)、MObject は addManipulator でコンテキストに渡す
- マニピュレータは普通、アトリビュート (プラグ) につないで値を動かすが、このツールは
  つながない。プラグを 1 つもつないでいないマニピュレータで finishAddingManips を呼ぶと
  kFailure になる (ウェイトスライダーで確認) ので、connectToDependNode も finishAddingManips も
  呼ばない
- ホバー: postConstructor で registerForMouseMove() を呼ぶと、マウスを動かすたびに doMove が
  呼ばれる。MPxContext にはマウスの移動のイベントが無いので、ホバーはこの仕組みで受け取る。
  押せる部品 (kSelectable) が 1 つも無いマニピュレータでも doMove は呼ばれる (旧版で確認)
- doMove の refresh 引数は Python からは書き戻せないので、変わったときは view.refresh で描き直す
- 描画: preDrawUI(view) が描く直前に呼ばれ (M3dView が来るのでカメラを読む)、
  drawUI(drawMgr, frameContext) で実際に描く。ビューを描き直すたびに Maya が呼ぶので、
  カメラを回しても表示が残る
- ボタン以外は kNonSelectable なので、メッシュの上のクリックはコンテキストの doPress に届く
"""
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui

from ..core import draw_list
from ..core.actions import ACTIONS, MODE_PATH, MODE_RING, MODE_SELECT, visible_actions
from ..core.panel import button_at, button_state, panel_layout
from ..core.picking import PICK_EDGE, pick_component
from ..core.session import preview_label, waypoint_label, waypoint_of
from .drawing import (PLANE_NEAR_RATIO, ScreenPlane, color_management_key, render, render_panel,
                      view_projector, view_ray)

__all__ = ["UVPathManip"]


class UVPathManip(omui.MPxManipulatorNode):
    """マウスの下の頂点 / エッジと、スタートからのパスのプレビューを描くマニピュレータ。

    押せる部品は持たない (クリックはコンテキストの doPress が受け取る)。
    """

    def __init__(self):
        super().__init__()
        self._targets = None  # scene.targets.TargetSet (対象のメッシュ。段階 14)
        self._start_state = None   # () -> (スタートのメッシュ, セッション) か (None, None)
        self._pick_target = None   # 拾ったもののメッシュ (MeshTarget)
        self._mode = PICK_EDGE   # 拾うもの (コンテキストが setPickMode で渡す)
        self._tool_mode = MODE_PATH   # モード (パス / 選択。コンテキストが setMode で渡す。段階 16)
        self._mouse = None    # 最後のマウスの位置 (モードを替えたときに拾い直すため)
        self._pick = None     # core.picking.Pick (マウスの下の頂点 / エッジ。無ければ None)
        self._preview = None  # スタートからマウスの下までのパス (core.path.PathResult か None)
        self._loop = []       # 選択のモードのループのプレビュー [(p0, p1)] (段階 16)
        self._loop_enabled = False   # ループのプレビューを出すか (設定 loopPreview)
        self._mirror_provider = None   # (MeshTarget) -> MirrorMap か None (段階 17)
        self._mirror_items = draw_list.DrawList()   # 反対側の描く一覧 (プレビューが変わったときに作る)
        self._selection_mirror = draw_list.DrawList()   # 選んだエッジの反対側 (選択のモード。段階 17c)
        self._loop_edges = []   # ループのエッジの番号 (反対側を描くため)
        self._ring_preview = draw_list.DrawList()   # 輪切りのプレビュー (コンテキストが作る。段階 19)
        # ボタン (段階 10)
        self._state_provider = None   # () -> core.actions.ActionState (コンテキストが渡す)
        self._action_handler = None   # (操作の ID) -> None (ボタンを押して離したとき)
        self._first_handle = 0        # ボタンのハンドルの名前の最初 (glFirstHandle)
        self._layout = {}             # ボタンの画面の矩形 (core.panel.panel_layout)
        self._plane = None            # ScreenPlane (preDrawUI で作る)
        self._hover_button = None     # マウスが乗っているボタンの ID
        self._pressed_button = None   # 押して、まだ離していないボタンの ID
        self._colors = {}             # {役割: 色} (色の設定。コンテキストが setColors で渡す)
        self._sync = None             # () -> bool。外部の変更を取り込む (コンテキストの syncMesh。段階 13)
        self._eye = None      # カメラの位置 (ワールド。タプル。preDrawUI で読む)
        self._cm_key = None   # カラーマネジメントの設定 (preDrawUI で読む)

    # プラグインは registerNode に creator / initialize を渡す。creator はこのクラスを
    # 毎回引いて作る (plug-ins/uvPathCut.py)
    @staticmethod
    def initialize():
        pass   # アトリビュートは持たない

    def postConstructor(self):
        # マウスを動かしたときに doMove を呼んでもらう (ホバーのため)
        self.registerForMouseMove()
        # ボタンのハンドルの名前は glFirstHandle() から順に使う (操作の表の番号を足す)
        self._first_handle = self.glFirstHandle()

    def setColors(self, colors):
        """色の設定 ({役割: 色}。core.draw_list.theme_colors) を受け取る。"""
        self._colors = dict(colors)

    def setPanel(self, state_provider, action_handler):
        """ボタンの文字・押せるかを決める状態の取り方と、押したときの処理 (段階 10)。"""
        self._state_provider = state_provider
        self._action_handler = action_handler

    def setMirrorProvider(self, provider):
        """対応表の引き方 (コンテキストの mirrorFor。対称がオフなら None を返す。段階 17)。"""
        self._mirror_provider = provider
        self.updatePreview()

    def _mirror(self, target):
        if self._mirror_provider is None or target is None:
            return None
        try:
            return self._mirror_provider(target)
        except RuntimeError:
            return None   # メッシュが消えたなど

    def _update_mirror_items(self):
        """反対側の描く一覧を作り直す (パスのモード: プレビュー・スタート、どちらも: 拾ったもの・ループ)。"""
        items = draw_list.DrawList()
        start_target, session = self._start()
        if self._tool_mode == MODE_PATH and session is not None and session.start is not None:
            mirror = self._mirror(start_target)
            if mirror is not None:
                edges = mirror.edges(self._preview.edges)[0] if self._preview else []
                start = mirror.waypoint(session.start)
                items.extend(draw_list.mirror_items(session.graph, edges,
                                                    [start] if start is not None else []))
        if self._pick is not None and self._pick_target is not None:
            mirror = self._mirror(self._pick_target)
            if mirror is not None:
                other = mirror.waypoint(waypoint_of(self._pick))
                loop = mirror.edges(self._loop_edges)[0] if self._loop_edges else []
                items.extend(draw_list.mirror_items(self._pick_target.model.graph(), loop,
                                                    [other] if other is not None else []))
        self._mirror_items = items

    def setRingPreview(self, items):
        """輪切りのプレビューの描く一覧 (ループと反対側。コンテキストがドラッグ中に作る。段階 19)。"""
        self._ring_preview = items

    def renderRing(self, drawMgr):
        """輪切りのプレビューを、渡された drawMgr に描く (コンテキストの doDrag から。段階 19)。

        Maya はツールのドラッグ中、ツール自身の描画 (doDrag の drawMgr) しか描き直さず、マニピュレータの
        drawUI は次にビュー全体を描き直すまで呼ばない (GUI で確認: ドラッグ中にプレビューが出ず、ビューを
        動かすと出た)。ドラッグ中はコンテキストの描画の口に、同じ一覧を描く。カメラは押す前の drawUI で読んだもの。
        """
        if self._eye is not None:
            render(drawMgr, self._ring_preview, self._eye, self._cm_key, self._colors)

    def setSelectionMirror(self, items):
        """選んだエッジの反対側の描く一覧 (選択のモードで描く。コンテキストが選択の変更で作る。段階 17c)。"""
        self._selection_mirror = items

    def setSync(self, sync):
        """外部の変更を取り込む関数 (段階 13)。描く前とマウスの移動で呼ぶ。"""
        self._sync = sync

    def _sync_mesh(self):
        return self._sync() if self._sync is not None else False

    def setTargets(self, targets, start_state):
        """対象のメッシュ (TargetSet) と、スタートの状態の取り方 (段階 14)。"""
        self._targets = targets
        self._start_state = start_state
        self.clearPick()

    def clearPick(self):
        """拾ったもの・プレビューを捨てる (メッシュ・対象が変わったとき。次のマウスの移動で拾い直す)。"""
        self._pick = None
        self._pick_target = None
        self._preview = None
        self._loop = []
        self._mirror_items = draw_list.DrawList()

    def _start(self):
        return self._start_state() if self._start_state is not None else (None, None)

    def preview(self):
        return self._preview

    def updatePreview(self):
        """スタートからマウスの下までのパスを引き直す (スタートが変わったとき・拾ったものが変わったとき)。

        セッションがスタートからの PathTree を持っているので、ここは道をたどるだけ (探し直さない)。
        """
        if self._tool_mode == MODE_SELECT:
            self._update_loop()
        elif self._tool_mode == MODE_RING:
            self._preview, self._loop, self._loop_edges = None, [], []
        else:
            start_target, session = self._start()
            pick = self._pick
            if pick is None or session is None or self._pick_target is not start_target:
                self._preview = None   # 別のメッシュの上ではプレビューしない (またぐパスは無い)
            else:
                self._preview = session.pathTo(waypoint_of(pick))
        self._update_mirror_items()

    def _update_loop(self):
        """選択のモード: マウスの下のエッジからのループを引き直す (段階 16)。"""
        self._preview = None
        self._loop_edges = []
        if not self._loop_enabled or self._pick is None or self._pick_target is None:
            self._loop = []
            return
        model = self._pick_target.model
        try:
            self._loop_edges = model.edgeLoop(self._pick.index)
            self._loop = model.edgeSegments(self._loop_edges)
        except RuntimeError:
            self._loop, self._loop_edges = [], []   # メッシュが消えたなど

    def loop(self):
        return self._loop

    def setLoopPreview(self, enabled):
        """ループのプレビューを出すか (設定 loopPreview)。オフならエッジ 1 本だけを強調する。"""
        self._loop_enabled = bool(enabled)
        if self._tool_mode == MODE_SELECT:
            self.updatePreview()   # ループと、その反対側を作り直す

    def _pick_kind(self):
        """拾うもの。選択のモードはいつもエッジ (選択のモードはエッジだけ。段階 16)。"""
        return PICK_EDGE if self._tool_mode == MODE_SELECT else self._mode

    def setPickMode(self, mode):
        """拾うもの (PICK_VERTEX / PICK_EDGE) を替え、最後のマウスの位置で拾い直す。"""
        self._mode = mode
        if self._mouse is not None and self._targets is not None:
            self._update_pick(omui.M3dView.active3dView(), *self._mouse)

    def setMode(self, mode):
        """モード (パス / 選択) を替える。拾ったもの・プレビューは捨てる (段階 16)。"""
        self._tool_mode = mode
        self.clearPick()
        self._hover_button = None
        self._ring_preview = draw_list.DrawList()

    def mode(self):
        return self._tool_mode

    def _visible(self):
        return visible_actions(self._tool_mode)

    def pick(self):
        return self._pick

    def pickTarget(self):
        """拾ったもののメッシュ (MeshTarget。段階 14)。"""
        return self._pick_target

    # -- マウス -----------------------------------------------------------------

    def modelValid(self):
        """対象のメッシュが 1 つでもシーンにあるか (無ければ、拾わない・描かない)。"""
        return self._targets is not None and bool(self._targets.valid())

    def doMove(self, view, refresh):
        # マウスを動かすたびに呼ばれる (registerForMouseMove したので)
        if self._targets is None:
            return
        x, y = self.mousePosition()
        self._mouse = (x, y)
        self._sync_mesh()   # 変わっていれば、新しいグラフ・セッションで拾い直す
        self._update_pick(view, x, y)

    def _update_pick(self, view, x, y):
        # ボタンの上なら、メッシュは拾わない (ボタンの奥の頂点 / エッジを確定しないため)
        self._layout = panel_layout(view.portWidth(), view.portHeight(), self._visible())
        button = button_at(self._layout, x, y)
        button_changed = button != self._hover_button
        self._hover_button = button
        source, direction = view_ray(view, x, y)
        try:
            # ボタンの上では拾わない。対象のメッシュすべてで、いちばん手前の面
            # 輪切りのモードは拾わない (線を描く。段階 19)
            target, hit = (self._targets.hit(source, direction)
                           if button is None and self._tool_mode != MODE_RING else (None, None))
            pick = None
            kind = self._pick_kind()
            if hit is not None:
                # 辺は頂点のモードでは使わないので、エッジのモードのときだけ読む
                edges = target.model.face_edges(hit.face) if kind == PICK_EDGE else []
                pick = pick_component(hit, edges, kind, (x, y), view_projector(view))
        except RuntimeError:
            target, pick = None, None   # メッシュが消えたなど
        if pick is None:
            target = None
        old, old_target = self._pick, self._pick_target
        self._pick, self._pick_target = pick, target
        # 番号はメッシュごとなので、メッシュも目印に入れる
        before = (old_target, old.key(), old.hit.key()) if old else None
        after = (target, pick.key(), pick.hit.key()) if pick else None
        if before != after:
            if (before[:2] if before else None) != (after[:2] if after else None):
                self.updatePreview()   # 拾ったものが変わったときだけ、道をたどり直す
            view.refresh(False, True)   # 拾ったもの (か面) が変わったときだけ描き直す
        elif button_changed:
            view.refresh(False, True)   # ボタンの明るさを描き直す

    # -- ボタン (段階 10) ---------------------------------------------------------

    def doPress(self, view):
        # ボタン (kSelectable で描いたもの) の上で押したときだけ呼ばれる。
        # 実行は離したとき (押したまま外へ動かしたらやめられるように)
        index = self.glActiveName() - self._first_handle
        self._pressed_button = ACTIONS[index].id if 0 <= index < len(ACTIONS) else None
        view.refresh(False, True)

    def doDrag(self, view):
        # 押している間は doMove が呼ばれないので、ここでマウスの下のボタンを調べ直す
        # (押したボタンの外へ出たら、押した色をやめる)
        x, y = self.mousePosition()
        button = button_at(self._layout, x, y)
        if button != self._hover_button:
            self._hover_button = button
            view.refresh(False, True)

    def doRelease(self, view):
        action_id, self._pressed_button = self._pressed_button, None
        x, y = self.mousePosition()
        self._hover_button = button_at(self._layout, x, y)   # 外で離したら、ホバーの色も残さない
        if (action_id is not None and self._hover_button == action_id
                and self._action_handler is not None):
            self._action_handler(action_id)   # 押せない操作はコンテキストが無視する
        view.refresh(False, True)

    # -- 描画 -------------------------------------------------------------------

    def preDrawUI(self, view):
        # 描く直前に呼ばれる。drawUI には M3dView が来ないので、カメラはここで読む
        # 外部の変更 (チャンネルボックスでの移動・再生での変形など。マウスが動かなくても描き直しは来る)
        # 変わっていれば、拾ったもの・プレビューは setModel で捨ててある (マウスを動かせば拾い直す。
        # 描いている途中で view.refresh を呼ばないよう、ここでは拾い直さない)
        self._sync_mesh()
        camera = om.MFnCamera(view.getCamera())
        eye = camera.eyePoint(om.MSpace.kWorld)
        self._eye = (eye.x, eye.y, eye.z)
        self._cm_key = color_management_key()
        self._layout = panel_layout(view.portWidth(), view.portHeight(), self._visible())
        # ボタンの平面はニアクリップのすぐ奥 (手前のメッシュに隠れないように)
        self._plane = ScreenPlane(view, max(camera.nearClippingPlane * PLANE_NEAR_RATIO, 1e-3))

    def drawItems(self):
        """今描くものの一覧 (core.draw_list.DrawList)。描く順 = 下から (段階ごとに足していく)。

        確定した区間 (いちばん下) -> パスのプレビュー -> スタート -> マウスの下の面と拾ったもの (上)。
        """
        items = draw_list.DrawList()
        if not self.modelValid():
            return items   # メッシュが消えたら何も描かない (Undo で戻れば、また描く)
        for _target, target_session in self._targets.sessions():
            if target_session.segments:   # 区間は全メッシュの分
                items.extend(draw_list.segment_items(target_session.graph, target_session.segments))
        items.extend(self._mirror_items)   # 反対側 (うすく。段階 17)
        if self._tool_mode == MODE_SELECT:
            items.extend(self._selection_mirror)   # 選んだエッジの反対側 (カットされるもの)
        if self._tool_mode == MODE_RING:
            items.extend(self._ring_preview)   # 輪切りのループ (段階 19)
        start_target, session = self._start()
        # スタートとプレビューはパスのモードだけ (選択のモードでも、スタートは覚えておく)
        start = session.start if session is not None and self._tool_mode == MODE_PATH else None
        if start is not None:
            items.extend(draw_list.path_items(session.graph, self._preview))
            items.extend(draw_list.waypoint_items(
                draw_list.endpoint_points(session.graph, start), draw_list.ROLE_START,
                "スタート " + waypoint_label(start)))
        if self._pick is not None and self._tool_mode == MODE_SELECT:
            if self._loop_enabled:
                items.extend(draw_list.loop_items(self._pick, self._loop))   # ループのプレビュー
            else:
                items.extend(draw_list.hover_items(self._pick))   # エッジ 1 本 (クリックで選ばれるもの)
        elif self._pick is not None:
            same_mesh = start is not None and self._pick_target is start_target
            label = preview_label(self._pick, self._preview, same_mesh)
            items.extend(draw_list.hover_items(self._pick, label))
        return items

    def panelButtons(self):
        """ボタンの [(操作の ID, 文字, 押せるか, 状態の名前)] (今のモードで見えるもの。表の順)。"""
        if self._state_provider is None:
            return []
        state = self._state_provider()
        buttons = []
        for action in self._visible():
            enabled = action.enabled(state)
            buttons.append((action.id, action.label(state), enabled,
                            button_state(action.id, enabled, self._hover_button,
                                         self._pressed_button)))
        return buttons

    def drawUI(self, drawMgr, frameContext):
        if self._eye is None:
            return
        render(drawMgr, self.drawItems(), self._eye, self._cm_key, self._colors)
        if self._plane is not None:
            render_panel(drawMgr, self._plane, self._layout, self.panelButtons(),
                         self._first_handle, self._cm_key)
