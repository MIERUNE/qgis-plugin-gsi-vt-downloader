# qgis-plugin-template

QGIS3.x プラグイン開発のひな形

## Preparation

1. install `uv`
   - <https://docs.astral.sh/uv/#getting-started>

2. install dependencies with uv

    ```sh
    # macOS
    uv venv --python /Applications/QGIS.app/Contents/MacOS/bin/python3 --system-site-packages
    
    # Windows 適切なバージョンのQGISのディレクトリを参照すること
    uv venv --python C:\Program Files\QGIS 3.28.2\apps\Python39\python.exe --system-site-packages
    ```

    仮想環境がカレントディレクトリに`.venv`フォルダとして作成されます。

3. (when VSCode) 仮想環境をVSCode上のPythonインタプリタとして選択

    VSCodeはカレントディレクトリの仮想環境を検出しますが、手動で選択する必要がある場合もあります。  

    1. [Cmd + Shift + P]でコマンドパレットを開く
    2. [Python: Select Interpreter]を見つけてクリック
    3. 利用可能なインタプリタ一覧が表示されるので、先ほど作成した仮想環境`/.venv/bin/python`を選択（通常、リストの一番上に"Recommended"として表示される）

## Tips

- 関心ごとに応じて、モジュールを分割しましょう（例：`ui`モジュール）
- `relative import`の利用を推奨します：以下のような絶対パスによるインポートは[Plugin Reloader](https://plugins.qgis.org/plugins/plugin_reloader/)で変更が反映されなくなることがあります（[Issue #16](https://github.com/MIERUNE/qgis-plugin-template/issues/16)）

    ```python
    # root.py
    from child import Child # NG
    from .child import Child # OK

    # child.py
    from grand_child import GrandChild # 子要素がその子要素インポートする際も同様
    from .grand_child import GrandChild # OK
    ```

- `ui`ファイルから生成されるインスタンスには型定義がありません。以下のようなコードで型定義を手動で当てることが出来ます。

    ```python
    class DialogType:
        # 型定義：UIファイルで定義されていてPythonから操作したいインスタンスはここに定義する
        # 生成AIに任せてもそこそこまともに出力してくれます
        verticalLayout: QVBoxLayout
        lineEdit: QLineEdit
        horizontalLayout: QHBoxLayout
        pushButton_run: QPushButton
        pushButton_cancel: QPushButton


    class Dialog(QDialog):
        def __init__(self):
            super().__init__()

            # 強制的に型キャスト：型の正しさは開発者の責任
            self.ui = cast(
                DialogType,
                uic.loadUi(os.path.join(os.path.dirname(__file__), "dialog.ui"), self),
            )

            self.ui.pushButton_run.clicked.connect(self.get_and_show_input_text)
            self.ui.pushButton_cancel.clicked.connect(self.close)
    ```
