<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS><TS version="2.0" language="ja_JP" sourcelanguage="">
<context>
    <name>GSIVectorTileDownloadAlgorithm</name>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="49"/>
        <source>This QGIS plugin downloads vector tiles from the Geospatial Information Authority of Japan (GSI) and adds them as a layer to QGIS. You can find information about the GSI Vector Tiles on the following site: &lt;a href=&apos;https://maps.gsi.go.jp/development/vt.html&apos;&gt;https://maps.gsi.go.jp/development/vt.html&lt;/a&gt;</source>
        <translation>このQGISプラグインは、国土地理院（GSI）のベクトルタイルをダウンロードし、QGISにレイヤとして追加します。
        国土地理院ベクトルタイルに関する情報は、以下のサイトから確認できます。
        &lt;a href=&apos;https://maps.gsi.go.jp/development/vt.html&apos;&gt;https://maps.gsi.go.jp/development/vt.html&lt;/a&gt;</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="55"/>
        <source>Download extent</source>
        <translation>ダウンロード範囲</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="69"/>
        <source>Source layers</source>
        <translation>ソースレイヤ</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="80"/>
        <source>Zoom level</source>
        <translation>ズームレベル</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="92"/>
        <source>Destination folder</source>
        <translation>出力フォルダ</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="120"/>
        <source>Successfully transformed extent to EPSG:4326</source>
        <translation>指定範囲をEPSG:4326へ正常に変換しました。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="124"/>
        <source>Coordinate transformation error: {error}</source>
        <translation>座標変換エラー：{error}</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="157"/>
        <source>Downloading {layer_key} at zoom level {zoom_level}</source>
        <translation>{layer_key} をズームレベル {zoom_level} でダウンロードしています。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="169"/>
        <source>No tiles found for the specified extent</source>
        <translation>指定された範囲にタイルが見つかりませんでした。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="174"/>
        <source>Found {count} tiles to download</source>
        <translation>ダウンロードするタイルが{count}個ありました。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="179"/>
        <source>Too many tiles to download (Tiles limit: {limit}).
</source>
        <translation>ダウンロードするタイルが多すぎます (Tiles limit: {limit}。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="179"/>
        <source>Please specify a zoom level lower than z{zoom} </source>
        <translation>ズームレベルを z{zoom} より小さい値を指定するか、</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="179"/>
        <source>or a smaller extent.
Process stopping...</source>
        <translation>より狭い範囲を指定してください。処理を停止します...</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="197"/>
        <source>No valid features found in the specified area</source>
        <translation>指定された範囲に有効な地物がありませんでした。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="205"/>
        <source>&#xe2;&#x9c;&#x93; Successfully clipped features to specified extent</source>
        <translation>指定範囲で正常にクリップされました。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="208"/>
        <source>Final feature count: {}</source>
        <translation>最終的な地物数: {}</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="230"/>
        <source>File saved : {}</source>
        <translation>ファイルを保存しました: {}</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="236"/>
        <source>Failed to save {}. Result : {}</source>
        <translation>{} の保存に失敗しました。結果: {}</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="250"/>
        <source>The following layers could not be downloaded:
</source>
        <translation>以下のレイヤがダウンロードされませんでした。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="520"/>
        <source>Using single layer</source>
        <translation>単一レイヤを使用</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="522"/>
        <source>Merging {} layers</source>
        <translation>{} レイヤをマージしています。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="565"/>
        <source>Load GSI Vector Tiles</source>
        <translation>国土地理院ベクトルタイルの地物を追加</translation>
    </message>
</context>
<context>
    <name>GSIVectorTileProvider</name>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_provider.py" line="18"/>
        <source>Load GSI Vector Tiles</source>
        <translation type="obsolete">国土地理院ベクトルタイルの地物を追加</translation>
    </message>
</context>
<context>
    <name>VTDownloader</name>
    <message>
        <location filename="../vtdownloader.py" line="51"/>
        <source>Load GSI vector tiles</source>
        <translation>国土地理院ベクトルタイルの地物を追加</translation>
    </message>
</context>
</TS>
