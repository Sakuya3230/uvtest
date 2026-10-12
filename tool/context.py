# -*- coding: utf-8 -*-
"""
コンテキスト (ツール本体)・コンテキストのコマンド・ツールのコマンド。

段階 0: ツールを有効 / 無効にしたことをスクリプトエディタに出すだけ。
段階 1: 設定 (core/settings.py の Settings) を持ち、optionVar に保存する。
        コンテキストのコマンドの編集 / 問い合わせのフラグを、設定の定義表から作る。
段階 2: ツールを有効にしたとき、選んでいるメッシュを対象にして、エッジの選択モードにする
        (scene/mesh.py)。メッシュが無ければ警告を出す。
段階 3: 対象の MeshModel とマニピュレータ (tool/manipulator.py) を作り、マウスの下の面を描く。
        ツールを無効にしたら、マニピュレータを消して MeshModel のコールバックを外す。
段階 4: 設定 pickMode をマニピュレータに渡す。設定が変わったら、リスナーで渡し直す
        (マニピュレータはその場で拾い直す)。
段階 7: クリックでスタートを決め、パスのプレビューを出す (core.session.PathSession)。
        doPress / doDrag / doRelease を上書きし、メッシュの上の修飾キーなしの左クリックは
        このツールが受け取る (基底を呼ばないので選択は変わらない)。それ以外は普通の選択。
        2 回目のクリックはパスをスクリプトエディタに出し、エンドを次のスタートにする
        (シーンの変更と Undo は段階 8)。Esc (abortAction) でスタートを取り消す。
段階 8: 2 回目以降のクリックで確定する (scene.edit.confirm_path。1 回の Undo で、区間を積み・
        スタートを進め・確定した区間すべてのエッジを選ぶ)。Undo / Redo でセッションが変わると、
        セッションのリスナー (_on_session_changed) で表示を更新する。
段階 9: 自動カット (設定 autoCut) なら、確定と同じ Undo の中で設定 operation (カット / 縫合) を
        行う。自動でなければ区間をためておき、-apply cut / -apply sew でまとめて実行する
        (1 回の Undo。ボタンとキーは段階 10・11)。
段階 10: ビューのボタン (操作の表 core.actions)。runAction(ID) が表を引いて、設定を切り替えるか
        コンテキストのメソッドを呼ぶ。リセット (clearAll。-clear フラグ) は区間・スタート・選択を
        すべて外す (1 回の Undo。UV のカットは戻さない)。
段階 11: キー (操作の表の key。tool/keys.py の Qt のフィルター)。ツールを有効にしている間だけ、
        マウスが 3D ビューの上にあるときに受け取り、runAction に渡す。ヘルプラインの文字も表から作る。
段階 12: ツール設定のウィンドウ (tool/tool_ui.py。MEL は core/tool_ui_text.py が表から組み立てる)。
        stringClassName() が "uvPathCut" なので、Maya は uvPathCutProperties / uvPathCutValues を呼ぶ。
        ウィンドウのボタンは -runAction <ID> で runAction を呼ぶ (ビューのボタン・キーと同じ経路)。
        ボタン・キーで設定を変えたら、開いているウィンドウの値も合わせる (tool_ui.refresh)。
        色の設定 (COLOR) は -setColor "キー r g b" で変え、マニピュレータに渡して描き直す。
段階 13: 外部の変更 (syncMesh)。マニピュレータが描く前・マウスを動かしたとき、クリック・操作の前に
        MeshModel.sync() を呼ぶ。位置が変わったらセッションのグラフを入れ替え、トポロジーが変わったら
        そのトポロジーのセッション (core.sync.SessionBook) に替える (元のトポロジーに戻れば前の区間が戻る)。
        対象は MDagPath で持ち、名前を変えられても今の名前で操作する (target は model.name())。
段階 14: 複数のメッシュ (scene.targets.TargetSet)。対象は選択とハイライトのメッシュすべてで、
        選択の変更の通知 (SelectionChanged) のあと手すきのときに決め直す (選んだメッシュはハイライトして
        加える)。メッシュごとにセッション (トポロジーごと) を持ち、スタートは全体で 1 つ (start_target)。
        確定の選択・まとめて実行・クリアは全メッシュが対象 (1 回の Undo)。
段階 16: モード (設定 mode。Tab)。パスのモードは今までどおり。選択のモードの選択は 16d からツールが行う。
        選択のモードに入ったら、対象をエッジの選択モードにし直す。
        カット / 縫合 (applyOperation。C / S・ボタン・-apply) は、パスのモードではためた区間、
        選択のモードでは選んでいるエッジ (全メッシュで 1 回の Undo。覆われた未実行の区間にも印)。
段階 17: シンメトリ (設定 symmetry / mirrorSpace / mirrorAxis)。対称の面は scene.mirror.mirror_plane、
        対応表はメッシュごとに mirrorFor で引く (覚えておいたものを使い回す)。ツールに入ったら、手すきの
        ときに対象の対応表を先に作る (_prebuild_mirrors)。
段階 17c: 選択のモードでも対称が効く。カット / 縫合は選んだエッジに反対側を足し、選んだエッジの反対側を
        うすく描く (選択が変わったとき・対称の設定が変わったときに updateSelectionMirror で作り直す)。
段階 16d: 選択のモードの選択はツールが行う (クリック・修飾キー・ダブルクリックのループ・矩形)。拾い方・ループ・
        反対側はプレビューと同じものを使うので、表示と結果が必ず一致する (Maya の選択に任せていた版の
        ダブルクリックの有効化・カメラベースの選択の切り替えは外した)。ダブルクリックは Qt のイベント (keys)。
段階 15: 設定 straightness (曲がりの重み) をセッションに渡す (core.turning)。変えたら全セッションへ。

段階 19: 輪切りのモード (tool/ring.py の RingMixin)。左ボタンのドラッグで線を描き、一周のループをプレビュー、
        クリックで確定 (ためる)。Esc でプレビューを捨てる。
段階 18: 役割ごとにモジュールを分けた。選択のモードの選択は tool/selecting.py (SelectingMixin)、対称は
        tool/symmetry.py (SymmetryMixin)、コンテキストのコマンドとツールのコマンドは tool/command.py
        (プラグインのため、このモジュールからも同じ名前を引ける)。UV を変えられないメッシュ (ロック) は
        飛ばして警告し、思わぬ失敗も警告にする (_run_edit)。

仕組み:
- Maya の「ツール」は、コンテキスト (MPxContext の派生) のインスタンス。コンテキストは
  コンテキストのコマンド (MPxContextCommand。ここでは uvPathCutCtx) で作る。
  cmds.uvPathCutCtx("名前") を呼ぶと、Maya が UVPathCutContextCommand を作って makeObj を呼び、
  返したインスタンスがその名前のツールになる。cmds.setToolTo("名前") で使い始める
- 同じコマンドに edit=True / query=True を付けると、Maya は makeObj を呼ばずに、
  そのツールを作ったときのコマンドのインスタンスの doEditFlags / doQueryFlags を呼ぶ
  (コマンドのインスタンスはツールごとに 1 つ残る。だから self._context でツールに届く)。
  使えるフラグは appendSyntax で足す
- MPxSelectionContext は「選択ツールに機能を足したコンテキスト」。マウスの処理を上書き
  しなければ、クリック・矩形・Shift / Ctrl の選択が標準の選択ツールと同じに動く
- toolOnSetup はツールを有効にしたとき、toolOffCleanup は別のツールにしたときに呼ばれる。
  API 2.0 では基底の toolOnSetup を super() で呼ぶと SystemError になる (旧版で確認) ので呼ばない
- クラスでは引数なしの super() を使う。super(クラス, self) だと、リロードのあとに古い
  インスタンスへイベントが届いたとき、名前が新しいクラスを指して TypeError になる
- これらのクラスはプラグインが直接登録しない。プラグインの creator がこのモジュールを
  毎回引いてインスタンスを作る (plug-ins/uvPathCut.py)。リロードしたあとに作るものは
  新しいクラスになる
"""
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.cmds as cmds
import maya.utils

from .. import log
from ..constants import MANIP_NODE
from ..core import accel
from ..core.actions import (MODE_PATH, MODE_RING, MODE_SELECT, ActionState, action_by_id, key_help,
                            next_setting_value)
from ..core.draw_list import COLOR_ROLES, theme_colors
from ..core.session import OPERATION_LABELS, PathSession, waypoint_of
from ..core.selection import ClickTracker, normalize_rect, selection_op
from ..core.sync import CHANGE_TOPOLOGY, STATUS_NEW, STATUS_RESTORED
from ..core.settings import Settings
from ..scene import edit as scene_edit
from ..scene import mesh as scene_mesh
from ..scene import mirror as scene_mirror
from ..scene import targets as scene_targets
from ..scene.prefs import OptionVarStorage
from . import keys
from . import tool_ui
from .command import (APPLY_FLAG, CLEAR_FLAG, RESET_COLORS_FLAG, RESET_FLAG, RUN_ACTION_FLAG,
                      SET_COLOR_FLAG, ToolCommand, UVPathCutContextCommand, delete_tool_context)
from .drawing import draw_marquee
from .manipulator import UVPathManip
from .selecting import (MARQUEE_THRESHOLD, SelectingMixin, double_click_interval,
                        event_position)
from .ring import RingMixin
from .symmetry import SymmetryMixin

__all__ = ["UVPathCutContext", "UVPathCutContextCommand", "ToolCommand", "delete_tool_context",
           "RESET_FLAG", "APPLY_FLAG", "CLEAR_FLAG", "RUN_ACTION_FLAG", "SET_COLOR_FLAG",
           "RESET_COLORS_FLAG"]

class UVPathCutContext(SelectingMixin, RingMixin, SymmetryMixin, omui.MPxSelectionContext):
    """ツールそのもの。

    メッシュの上 (マニピュレータが頂点 / エッジを拾っているとき) の修飾キーなしの左クリックは
    パスの操作、それ以外のマウスの操作は標準の選択と同じに働く。
    """

    def __init__(self):
        super().__init__()
        self.setTitleString("UV パスカット")
        # 作ったときに optionVar から読む。変えるたびに保存する
        self.settings = Settings(OptionVarStorage())
        self.settings.addListener(self._on_setting_changed)
        self.targets = None  # scene.targets.TargetSet (対象のメッシュ。ツールを有効にしている間。段階 14)
        self.start_target = None   # スタートを置いたメッシュ (MeshTarget。スタートは全体で 1 つ)
        self._manip = None   # UVPathManip (Python のインスタンス)
        self._selection_callback = None   # 選択の変更の通知 (対象のメッシュを増やすため。段階 14)
        self._targets_pending = False     # 対象を調べ直す予約 (executeDeferred) があるか
        self._consumed = False   # 今のマウスの操作をこのツールが受け取ったか (押してから離すまで)
        self._maya_symmetry = None   # 最後に見た Maya の対称の設定 (checkMayaSymmetry。段階 17)
        self._clicks = ClickTracker(double_click_interval())   # ダブルクリックを見分ける (段階 16d)
        self._press = None      # 選択のモード: 押した位置と修飾キー ((x, y), op)
        self._marquee = None    # 選択のモード: ドラッグ中の矩形 (左, 下, 右, 上)
        self._last_loop = None  # 最後にループを選んだ (メッシュ, エッジ, 時刻)。同じダブルクリックを 2 回扱わない
        self._ring_press = None    # 輪切り: 押した位置 (段階 19)
        self._ring_dragged = False
        self._ring_stroke = None   # 最後に探した線 (core.ring.Stroke)
        self._ring_found = None    # プレビューの (メッシュ, scene.ring.RingFound)
        self._ring_screens = []    # 押したときの [(メッシュ, scene.ring.RingTarget)]
        self._ring_rays = None     # (x, y) -> 視線 (始点, 向き)
        self._ring_plane = None    # 最後に作った切る面 (なめらかにする・微調整するとき)
        self._ring_view = None     # 視線の向き (縦の継ぎ目・傾けるとき)
        self._ring_seam = False    # 縦の継ぎ目か (Shift+ドラッグ。段階 21)
        self._ring_kept = []       # 離したあとの微調整に使う [(メッシュ, RingTarget)]
        self._last_click = None  # 最後のクリックの選択 (メッシュ, エッジ, 時刻, Undo の名前)。ダブルクリックで取り消す
        self._maya_checked = 0.0

    @property
    def session(self):
        """スタートを置いたメッシュの今のセッション (無ければ None)。"""
        target = self.start_target
        if self.targets is None or target is None or target not in self.targets.active:
            return None
        return target.session()

    @property
    def target(self):
        """スタートを置いたメッシュのシェイプの今のフルパス (無ければ None)。"""
        target = self.start_target
        return target.name() if target is not None and target.isValid() else None

    def stringClassName(self):
        # ツールの種類の名前。Maya はこの名前に Properties / Values を付けた MEL のプロシージャを
        # 呼んで、ツール設定のウィンドウを作る (tool/tool_ui.py)
        return tool_ui.CLASS_NAME

    def mode(self):
        """今のモード (MODE_PATH / MODE_SELECT。段階 16)。"""
        return self.settings.value("mode")

    def _help_text(self):
        if self.mode() == MODE_SELECT:
            head = ("UV パスカット (選択): クリックでエッジ、ダブルクリックでループ、ドラッグで矩形 "
                    "(Shift 切り替え / Ctrl 外す / Ctrl+Shift 足す)。ボタンでカット / 縫合")
        elif self.mode() == MODE_RING:
            head = ("UV パスカット (輪切り): 筒を横切るようにドラッグで一周 (Shift+ドラッグで縦の継ぎ目)、"
                    "ホイールでずらす / Shift+ホイールで傾ける、クリックで確定、Esc で捨てる")
        else:
            head = "UV パスカット (パス): クリックでスタート、次のクリックで確定。Esc スタートを取り消す"
        return head + "  " + key_help()

    def toolOnSetup(self, event):
        # 基底の toolOnSetup は呼ばない (API 2.0 では SystemError になる)
        self.setHelpString(self._help_text())
        shapes = scene_mesh.target_meshes()
        if not shapes:
            log.warning("メッシュを選んでからツールにしてください")
            return
        # 対象をエッジの選択モードにする (頂点 / エッジのどちらを拾うモードでも共通)
        scene_mesh.enter_edge_mode([scene_mesh.shape_transform(shape) for shape in shapes])
        self._maya_symmetry = scene_mirror.maya_symmetry()   # ボタンの表示用 (変更は checkMayaSymmetry)
        self.targets = scene_targets.TargetSet(self._new_session)
        self.targets.setShapes(shapes)
        self.start_target = None
        for shape in shapes:
            vertices, edges, faces = scene_mesh.mesh_counts(shape)
            log.info("対象 {} (頂点 {} / エッジ {} / フェース {})".format(shape, vertices, edges, faces))
            self._report_mesh(shape)
        log.info("設定 {}".format(self.settings.values()))
        log.info("最短パスの計算: {}".format(
            "scipy (スタートごとに全頂点を 1 回探す)" if accel.available()
            else "Python (ゴールごとに A*)"))
        self._create_manipulator()
        # 操作の表のキーと、選択のモードのダブルクリック (ビューの上にマウスがあるときだけ)
        keys.install(self.runAction, double_click=self.onDoubleClick, wheel=self.onWheel)
        # 対称の対応表を、手すきのときに先に作っておく (対称がオフでも。オンにした瞬間に使えるように)
        maya.utils.executeDeferred(self._prebuild_mirrors)
        # 選択が変わったら、選んだメッシュを対象に加える (段階 14)
        self._selection_callback = om.MEventMessage.addEventCallback(
            "SelectionChanged", self._on_selection_changed)

    def toolOffCleanup(self):
        # toolOnSetup と同じく、基底の toolOffCleanup は呼ばない
        keys.uninstall()   # 外さないと、ツールを抜けても Tab / C / S を取り続ける
        if self._selection_callback is not None:
            om.MMessage.removeCallback(self._selection_callback)
            self._selection_callback = None
        self.deleteManipulators()
        self._manip = None
        if self.targets is not None:
            # 抜けたあとの Undo / Redo は、表示されていないセッションを変えるだけ (知らせない)
            for target in self.targets.known:
                for session in target.sessions():
                    session.removeListener(self._on_session_changed)
            self.targets.release()   # dirty などのコールバックを外す
            self.targets = None      # 表示 (スタート・区間) はツールを抜けたら消す
        self.start_target = None
        self._consumed = False
        log.info("ツールを無効にしました")

    def _new_session(self, graph):
        """メッシュ (とトポロジー) ごとのセッションを作る (TargetSet が初めて使うときに呼ぶ)。"""
        session = PathSession(graph, turn_weight=self.settings.value("straightness"))
        # Undo / Redo でセッションが変わったら、表示を更新する (コマンドは表示のことを知らない)
        session.addListener(self._on_session_changed)
        return session

    # -- マウス -----------------------------------------------------------------

    def _wants_click(self, event):
        """この押下をパスの操作に使うか (パスのモードで、修飾キーなしの左クリックで、メッシュの上)。"""
        return (self.mode() == MODE_PATH
                and self._manip is not None and self._manip.modelValid()
                and self._manip.pick() is not None
                and event.mouseButton() == omui.MEvent.kLeftMouse
                and not (event.isModifierShift() or event.isModifierControl()))

    def _wants_selection(self, event):
        """選択のモードの左ボタンか (ツールが選ぶ。段階 16d)。"""
        return (self.mode() == MODE_SELECT and self.targets is not None
                and event.mouseButton() == omui.MEvent.kLeftMouse)

    def _wants_ring(self, event):
        """輪切りのモードの左ボタンか (線を描く。段階 19)。"""
        return (self.mode() == MODE_RING and self.targets is not None
                and event.mouseButton() == omui.MEvent.kLeftMouse)

    def doPress(self, event, drawMgr, context):
        # パスの操作・選択のモードの左ボタンは基底 (標準の選択) を呼ばない。呼ばなければ選択は変わらない。
        # 基底は omui.MPxSelectionContext.doPress(self, ...) と明示して呼ぶ (ウェイトスライダーで確認)
        self._press = None
        self._marquee = None
        if self._wants_ring(event):
            self._consumed = True
            self.ringPress(event_position(event), seam=event.isModifierShift())   # Shift = 縦の継ぎ目
            return
        if self._wants_selection(event):
            self._consumed = True
            self._press = (event_position(event),
                           selection_op(event.isModifierShift(), event.isModifierControl()))
            return
        self._consumed = self._wants_click(event)
        if not self._consumed:
            omui.MPxSelectionContext.doPress(self, event, drawMgr, context)

    def doDrag(self, event, drawMgr, context):
        if self._ring_press is not None:
            self.ringDrag(event_position(event), drawMgr)   # 線とプレビュー
            return
        if self._press is not None:
            # 選択のモード: 少し動かしたら矩形選択。枠はこの drawMgr に描く
            start = self._press[0]
            end = event_position(event)
            if self._marquee is not None or max(abs(end[0] - start[0]),
                                                abs(end[1] - start[1])) >= MARQUEE_THRESHOLD:
                self._marquee = normalize_rect(start, end)
                draw_marquee(drawMgr, self._marquee)
            return
        # 受け取った操作 (パス) では、矩形選択の枠も出さない
        if not self._consumed:
            omui.MPxSelectionContext.doDrag(self, event, drawMgr, context)

    def doRelease(self, event, drawMgr, context):
        if self._ring_press is not None:
            self._consumed = False
            self.ringRelease(event_position(event))
            return
        if self._wants_ring(event):
            return   # 輪切りのモード: 押下が届かなかった離しは何もしない
        if self._press is not None:
            press, self._press = self._press, None
            marquee, self._marquee = self._marquee, None
            self._consumed = False
            if marquee is not None:
                self.selectInRect(marquee, press[1])
            else:
                self.selectClick(self._manip.pickTarget() if self._manip else None,
                                 self._manip.pick() if self._manip else None, press[1])
            return
        if self._wants_selection(event):
            return   # 選択のモード: 押下が届かなかった離し (ダブルクリックの 2 回目) は何もしない
        if not self._consumed:
            omui.MPxSelectionContext.doRelease(self, event, drawMgr, context)
            return
        self._consumed = False
        self._click(self._manip.pickTarget(), self._manip.pick())

    def _click(self, target, pick):
        """拾ったもの (core.picking.Pick。target のメッシュ) をクリックした: スタートにするか、確定する。

        離したときのマウスの下のもので決める (押してから少し動かしても、見えているものを使う)。
        スタートを決めるだけなら Undo には積まない。確定は scene.edit.confirm_path で 1 回の Undo。
        スタートと違うメッシュをクリックしたら、そこを新しいスタートにする (メッシュをまたぐパスは無い)。
        """
        if pick is None or target is None:
            return
        if self.syncMesh():
            return   # メッシュが変わっていた (拾ったものは古い位置・番号なので使わない)
        waypoint = waypoint_of(pick)
        session = target.session(create=True)   # 初めてのメッシュなら、ここでグラフを作る
        if self.start_target is not target:
            self._clear_start()
        if session.start is None:
            session.setStart(waypoint)   # ここでスタートからの PathTree を作る
            self.start_target = target
            log.info("スタート {}  ({})".format(pick.label(), target.name()))
        elif waypoint == session.start:
            return   # スタートと同じものをクリックしても何もしない
        else:
            # 自動カットなら、確定と同じ Undo の中で設定の操作 (カット / 縫合) も行う
            operation = (self.settings.value("operation") if self.settings.value("autoCut")
                         else None)
            blocker = scene_mesh.edit_blocker(target.name()) if operation else None
            if blocker:
                log.warning("{}: {}。確定だけして、{}はしません".format(
                    target.name(), blocker, OPERATION_LABELS[operation]))
                operation = None
            segment = self._run_edit("確定", scene_edit.confirm_path, session, target.name(),
                                     waypoint, operation, others=self._other_edges(target),
                                     mirror=self.mirrorFor(target))
            if segment is None:
                log.warning("{} はスタートとつながっていません".format(pick.label()))
                return
            log.info("確定 {}  (スタック {} 区間 / エッジ {} 本)".format(
                segment, len(session.segments), len(session.edges())))
            if segment.mirror_missing:
                log.warning("反対側が見つからないエッジが {} 本あります (その分は片側だけ)".format(
                    segment.mirror_missing))
            return   # 表示はセッションのリスナー (_on_session_changed) が更新する
        self.refresh()

    def _clear_start(self):
        """今のスタートを外す (Undo には積まない。スタートは全体で 1 つ)。"""
        session = self.session
        if session is not None:
            session.clearStart()
        self.start_target = None

    def _other_edges(self, target):
        """target 以外の対象のメッシュの [(シェイプ, 区間のエッジ)] (確定のあとも選んだままにする)。"""
        return [(other.name(), session.edges()) for other, session in self.targets.sessions()
                if other is not target and session.segments]

    def applyPending(self, operation):
        """ためた (まだ実行していない) 区間を、全メッシュまとめてカット / 縫合する (1 回の Undo)。"""
        if self.targets is None:
            log.warning("ツールを使っているときだけ実行できます")
            return []
        pairs = [(session, target.name()) for target, session in self._editable_sessions()]
        segments = self._run_edit(OPERATION_LABELS[operation], scene_edit.apply_pending_all,
                                  pairs, operation) or []
        if not segments:
            log.warning("まだ{}していない区間がありません".format(OPERATION_LABELS[operation]))
        else:
            log.info("{} 区間を{}しました".format(len(segments), OPERATION_LABELS[operation]))
        return segments

    def applyOperation(self, operation):
        """カット / 縫合 (ボタン・キー・-apply)。モードで振り分ける (段階 16)。"""
        if self.mode() == MODE_SELECT:
            return self.applySelection(operation)
        return self.applyPending(operation)

    def applySelection(self, operation):
        """選んでいる、対象のメッシュのエッジをカット / 縫合する (全メッシュで 1 回の Undo。段階 16)。

        戻り値は (実行したエッジの数, 印を付けた区間の数)。
        """
        if self.targets is None:
            log.warning("ツールを使っているときだけ実行できます")
            return 0, 0
        pairs, ignored = self.targets.selectedEdges()
        if ignored:
            log.warning("エッジ以外の選択は使いません (エッジだけを対象にしました)")
        pairs = [(target, edges) for target, edges in pairs if self._editable(target)]
        items = [(target.name(), edges, target.session()) for target, edges in pairs]
        mirrors = {}
        missing = 0
        for target, edges in pairs:   # 対称がオンなら、反対側も (段階 17c)
            mirror = self.mirrorFor(target)
            if mirror is not None:
                mirrors[target.name()] = mirror
                missing += mirror.edges(edges)[1]
        count, marked = self._run_edit(OPERATION_LABELS[operation], scene_edit.apply_selection,
                                       items, operation, mirrors) or (0, 0)
        if missing:
            log.warning("反対側が見つからないエッジが {} 本あります (その分は片側だけ)".format(missing))
        label = OPERATION_LABELS[operation]
        if not count:
            log.warning("{}するエッジを選んでいません".format(label))
        else:
            message = "選んだエッジ {} 本を{}しました".format(count, label)
            if marked:
                message += " (未実行の区間 {} つも{}済みにしました)".format(marked, label)
            log.info(message)
        return count, marked

    # -- 扱えないメッシュ (段階 18) ------------------------------------------------------

    def _report_mesh(self, shape):
        """対象にしたメッシュについて、知らせておくことをログに出す (インスタンス・UV が無い・ロック)。"""
        for warning, text in scene_mesh.mesh_notes(shape):
            (log.warning if warning else log.info)("{}: {}".format(shape, text))

    def _editable(self, target):
        """UV を変えられるメッシュか。変えられなければ理由を警告して False。"""
        blocker = scene_mesh.edit_blocker(target.name())
        if blocker:
            log.warning("{}: {}。このメッシュはカット / 縫合しません".format(target.name(), blocker))
            return False
        return True

    def _editable_sessions(self):
        return [(t, s) for t, s in self.targets.sessions()
                if s.pendingSegments() and self._editable(t)]

    def _run_edit(self, label, function, *args, **kwargs):
        """シーンを変える関数 (scene.edit) を呼ぶ。失敗したら警告して None (変更は戻っている)。

        PathEditCommand は途中で失敗すると、行った分を戻してから例外を投げる (Undo のキューにも積まない)。
        ここで受け止めて、トレースバックではなく分かる文で知らせる。
        """
        try:
            return function(*args, **kwargs)
        except RuntimeError as error:
            log.warning("{}に失敗しました (変更は元に戻しました): {}".format(
                label, str(error).strip().splitlines()[-1] if str(error).strip() else error))
            return None

    def clearAll(self):
        """全メッシュの確定した区間・スタート・エッジの選択をすべて外す (1 回の Undo。段階 10)。"""
        if self.targets is None:
            log.warning("ツールを使っているときだけ実行できます")
            return None
        counts = scene_edit.clear_sessions([s for _t, s in self.targets.sessions()])
        if counts is None:
            self.refresh()
            return None
        segments, pending = counts
        message = "クリアしました ({} 区間".format(segments)
        if pending:
            message += "。まだカット / 縫合していなかった {} 区間を捨てました".format(pending)
        log.info(message + "。Ctrl+Z で戻せます)")
        return counts

    # -- 操作の表 (段階 10) -------------------------------------------------------

    def actionState(self):
        """ボタンの文字・押せるかを決める今の状態 (core.actions.ActionState。全メッシュの合計)。"""
        sessions = [s for _t, s in self.targets.sessions()] if self.targets is not None else []
        selected = 0
        if self.targets is not None and self.mode() == MODE_SELECT:
            selected = sum(len(edges) for _t, edges in self.targets.selectedEdges()[0])
        maya = scene_mirror.maya_plane(self._maya_symmetry) if self._maya_symmetry else None
        return ActionState(self.settings.values(), selected=selected,
                           maya_axis=maya.axis if maya is not None else None,
                           pending=sum(len(s.pendingSegments()) for s in sessions),
                           segments=sum(len(s.segments) for s in sessions),
                           has_start=self.session is not None and self.session.start is not None,
                           mesh_valid=bool(self.targets is not None and self.targets.valid()))

    def runAction(self, action_id):
        """操作 (ボタン・キー・ツール設定のウィンドウから) を行う。押せない状態なら何もしない。"""
        self.syncMesh()   # キーで押したときも、今のトポロジーのセッションで行う
        action = action_by_id(action_id)
        if not action.enabled(self.actionState()):
            return
        if action.setting is not None:
            key = action.setting
            value = (action.value if action.value is not None
                     else next_setting_value(key, self.settings.value(key)))
            self.settings.set(key, value)
            if key == "symmetry" and scene_mirror.maya_plane() is not None:
                log.warning("Maya の対称がオンなので、ツールの対称を切り替えても両側に効きます"
                            " (Maya の対称をオフにすると、ツールの対称に従います)")
        else:
            getattr(self, action.method)(*action.args)
        self._redraw()   # ボタンの文字を描き直す

    # -- 対象のメッシュ (段階 14) ---------------------------------------------------

    def _on_selection_changed(self, *args):
        # 通知の中ではシーンを変えない (ハイライトする)。手すきのときに 1 回だけ調べる
        if not self._targets_pending:
            self._targets_pending = True
            maya.utils.executeDeferred(self.updateTargets)

    def updateTargets(self):
        """選んだメッシュを対象に加え、対象のメッシュすべてをエッジを選べる状態 (ハイライト) にする。

        対象はツールを入れ直すまで増えるだけ (外さない)。オブジェクトの選択モードで別のメッシュを
        選ぶと、前のメッシュのハイライトが外れる (mayapy で確認) が、対象のまま・区間もそのままにして、
        ハイライトを付け直す。消したメッシュは描かないだけで、Undo で戻ればまた対象。
        自分の確定・カットで選択が変わったときも呼ばれるが、メッシュは同じなので何も変わらない。
        """
        self._targets_pending = False
        if self.targets is None:
            return   # ツールを抜けたあと
        added = self.targets.add(scene_mesh.target_meshes())
        hilited = set(scene_mesh.mesh_shape(n) for n in cmds.ls(hilite=True, long=True) or [])
        missing = [t.name() for t in self.targets.valid() if t.name() not in hilited]
        if missing:
            self._ensure_edge_mode(missing)   # エッジを選べる状態に戻す (Undo には積まない)
        for target in added:
            log.info("対象に加えました {}".format(target.name()))
            self._report_mesh(target.name())
        self.updateSelectionMirror()   # 選択が変わったので、反対側の表示を作り直す (段階 17c)
        if added:
            if self._manip is not None:
                self._manip.clearPick()
            self.refresh()
        else:
            self._redraw()

    # -- 外部の変更 (段階 13) -------------------------------------------------------

    def syncMesh(self):
        """外部の変更を取り込む。変わっていたら True (マニピュレータが描く前・マウスの移動で呼ぶ)。

        変わっていなければ (通知が無ければ) 何も読まないので、何度呼んでも軽い。
        メッシュごとに、位置が変わればグラフを入れ替え、トポロジーが変わればそのトポロジーの
        セッションに替える (scene.targets.MeshTarget.sync)。
        """
        if self.targets is None:
            return False
        self.checkMayaSymmetry()   # Maya の対称の変更 (表示だけ。段階 17)
        changes = self.targets.sync()
        if not changes:
            return False
        for target, kind, status in changes:
            if kind != CHANGE_TOPOLOGY or status is None:
                continue
            graph = target.model.graph()
            counts = "{} 頂点 {} / エッジ {}".format(target.name(), len(graph.points), len(graph.edges))
            if status == STATUS_RESTORED:
                log.info("前のトポロジーに戻ったので、そのときの区間に戻しました ({}。{} 区間)".format(
                    counts, len(target.session().segments)))
            elif status == STATUS_NEW:
                log.warning("メッシュのトポロジーが変わりました ({})。区間はここから別に記録します"
                            " (Undo などで元に戻せば、前の区間が戻ります)".format(counts))
        if self._manip is not None:
            self._manip.clearPick()   # 位置だけでも、拾ったもの・プレビューは古いので捨てる
        return True

    def _on_session_changed(self, session):
        # 確定・Undo・Redo でセッションが変わった (PathEditCommand が notify する)
        if self.targets is None:
            return
        owner = self.targets.owner(session)
        if owner is None or owner not in self.targets.active or owner.session() is not session:
            return   # 表示していないセッション (外れたメッシュ・前のトポロジー)
        if session.start is not None and owner is not self.start_target:
            # Undo で別のメッシュのスタートが戻った: スタートは全体で 1 つにする
            old = self.session
            if old is not None:
                old.clearStart()
            self.start_target = owner
        self.refresh()

    def refresh(self):
        """セッションが変わったときに、プレビューを引き直して描き直す。"""
        if self._manip is not None:
            self._manip.updatePreview()
        omui.M3dView.active3dView().refresh(False, True)

    def abortAction(self):
        # Esc で呼ばれる。輪切りのモードならプレビューを捨てる。ほかは未確定のスタートを取り消す
        if self.mode() == MODE_RING:
            if self.clearRing():
                log.info("輪切りのプレビューを捨てました")
                self._redraw()
            return
        if self.session is not None and self.session.start is not None:
            self._clear_start()
            log.info("スタートを取り消しました")
            self.refresh()

    def _create_manipulator(self):
        self.deleteManipulators()
        # newManipulator の引数は、プラグインが registerNode で登録したノードの型の名前。
        # (Python のインスタンス, MObject) が返る。インスタンスはプラグインの creator が作る
        # (このモジュールの今のクラス)
        manip, manip_object = UVPathManip.newManipulator(MANIP_NODE)
        self.addManipulator(manip_object)
        # connectToDependNode / finishAddingManips は呼ばない (プラグをつながないため)
        manip.setTargets(self.targets, self._start_state)
        manip.setMirrorProvider(self.mirrorFor)   # 反対側の表示 (段階 17)
        manip.setSync(self.syncMesh)   # 描く前・マウスの移動で外部の変更を取り込む (段階 13)
        manip.setPanel(self.actionState, self.runAction)
        manip.setColors(theme_colors(self.settings.values()))
        manip.setPickMode(self.settings.value("pickMode"))
        manip.setMode(self.mode())
        manip.setLoopPreview(self.settings.value("loopPreview"))
        self._manip = manip

    def _enter_mode(self, mode):
        """モードを替えたとき (段階 16)。マニピュレータに渡し、選択のモードなら対象をエッジの選択に戻す。"""
        self.setHelpString(self._help_text())
        if self._manip is not None:
            self._manip.setMode(mode)
        self.clearRing()   # 輪切りのプレビューはモードを替えたら捨てる
        if mode == MODE_SELECT and self.targets is not None:
            self._ensure_edge_mode([t.name() for t in self.targets.valid()])
        self._redraw()

    def _redraw(self):
        """ビューを描き直す (マニピュレータがあるときだけ。テストでは差し替える)。"""
        if self._manip is not None:
            omui.M3dView.active3dView().refresh(False, True)

    def _ensure_edge_mode(self, shapes):
        """メッシュをエッジの選択モード (ハイライト) にする。Undo には積まない。

        積むと、Ctrl+Z がハイライトを戻すだけになり、確定などの Undo が 1 回ずれる。
        """
        if not shapes:
            return
        state = cmds.undoInfo(query=True, stateWithoutFlush=True)
        cmds.undoInfo(stateWithoutFlush=False)
        try:
            scene_mesh.enter_edge_mode([scene_mesh.shape_transform(s) for s in shapes])
        finally:
            cmds.undoInfo(stateWithoutFlush=state)

    def _start_state(self):
        """(スタートを置いたメッシュ, そのセッション)。スタートが無ければ (None, None)。"""
        session = self.session
        if session is None or session.start is None:
            return None, None
        return self.start_target, session

    def _on_setting_changed(self, key, value):
        # 設定の変更を、使っている所へ届ける (段階ごとに足していく)
        log.info("{} = {!r}".format(key, value))
        tool_ui.refresh()   # ボタン・キーで変えたときも、開いているウィンドウの値を合わせる
        if key in COLOR_ROLES and self._manip is not None:
            self._manip.setColors(theme_colors(self.settings.values()))
            omui.M3dView.active3dView().refresh(False, True)
        if key == "pickMode" and self._manip is not None:
            self._manip.setPickMode(value)   # その場で拾い直して描き直す
        if key == "mode":
            self._enter_mode(value)
        if key == "loopPreview" and self._manip is not None:
            self._manip.setLoopPreview(value)
            self._redraw()
        if key in ("symmetry", "mirrorSpace", "mirrorAxis", "mirrorTolerance", "mode") \
                and self._manip is not None:
            self._manip.updatePreview()   # 反対側の表示を作り直す
            self.updateSelectionMirror()
            self._redraw()
        if key == "straightness" and self.targets is not None:
            # 全メッシュ・全トポロジーのセッションに渡す (スタートがあれば、そこで探し直す)
            for target in self.targets.known:
                for session in target.sessions():
                    session.setTurnWeight(value)
            self.refresh()   # プレビューを新しい重みで引き直す
