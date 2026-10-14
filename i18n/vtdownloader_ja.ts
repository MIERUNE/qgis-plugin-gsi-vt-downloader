<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS><TS version="2.0" language="ja_JP" sourcelanguage="">
<context>
    <name>GSIVectorTileDownloadAlgorithm</name>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="72"/>
        <source>Downloads GSI Japan vector tiles to GeoPackage.
Fetches the tiles covering the extent (any CRS) at the zoom level and saves the features intersecting the extent of each selected source layer (e.g. road, building, contour) as one file in the destination folder (e.g. road_z14.gpkg).
OUTPUT_LAYERS returns the saved file paths. The files are added to the project when results are loaded (e.g. from the toolbox), but not by processing.run().
Source layers with no features in the extent are skipped. The run fails if the zoom level is outside the range of a selected layer (e.g. building: z13-16), more than {limit} tiles are needed, a tile fails to download after retries, or no features are found at all.
Tile specification: &lt;a href=&apos;https://maps.gsi.go.jp/development/vt.html&apos;&gt;https://maps.gsi.go.jp/development/vt.html&lt;/a&gt;</source>
        <translation>指定範囲の国土地理院ベクトルタイルをダウンロードし、GeoPackageに保存します。
範囲（任意のCRS）をズームレベルで覆うタイルを取得し、選択したソースレイヤ（道路・建物・等高線など）ごとに、範囲と交差する地物を出力フォルダの1ファイル（例: road_z14.gpkg）に保存します。
OUTPUT_LAYERS は保存したファイルのパスを返します。結果を読み込む実行（ツールボックスなど）ではプロジェクトに追加されますが、processing.run() では追加されません。
範囲内に地物がないソースレイヤはスキップされます。ズームレベルが選択したレイヤの対応範囲外（例: building は z13〜16）の場合、必要なタイル数が {limit} を超える場合、再試行してもタイルをダウンロードできない場合、地物が1つも見つからない場合は失敗します。
タイル仕様: &lt;a href=&apos;https://maps.gsi.go.jp/development/vt.html&apos;&gt;https://maps.gsi.go.jp/development/vt.html&lt;/a&gt;</translation>
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
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="117"/>
        <source>Output layers</source>
        <translation>出力レイヤ</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="146"/>
        <source>The extent has no CRS. It is assumed to be EPSG:4326.</source>
        <translation>ダウンロード範囲に座標参照系が設定されていないため、EPSG:4326 とみなします。</translation>
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
        <translation type="obsolete">{layer_key} をズームレベル {zoom_level} でダウンロードしています。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="176"/>
        <source>Extracting {layer_key} at zoom level {zoom_level}</source>
        <translation>{layer_key} をズームレベル {zoom_level} で抽出しています。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="246"/>
        <source>Zoom level z{zoom} is not available for: {layers}</source>
        <translation>次のレイヤはズームレベル z{zoom} に対応していません: {layers}</translation>
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
        <translation type="obsolete">ダウンロードするタイルが多すぎます (Tiles limit: {limit}。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="179"/>
        <source>Please specify a zoom level lower than z{zoom} </source>
        <translation type="obsolete">ズームレベルを z{zoom} より小さい値を指定するか、</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="179"/>
        <source>or a smaller extent.
Process stopping...</source>
        <translation type="obsolete">より狭い範囲を指定してください。処理を停止します...</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="267"/>
        <source>Too many tiles to download ({count} tiles, limit: {limit}). Specify a lower zoom level or a smaller extent.</source>
        <translation>ダウンロードするタイルが多すぎます（{count} 個、上限 {limit} 個）。ズームレベルを下げるか、範囲を狭めてください。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="403"/>
        <source>Could not download tile {z}/{x}/{y} after {attempts} attempts: {error}</source>
        <translation>タイル {z}/{x}/{y} を {attempts} 回試しましたが、ダウンロードできませんでした: {error}</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="197"/>
        <source>No valid features found in the specified area</source>
        <translation>指定された範囲に有効な地物がありませんでした。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="205"/>
        <source>&#xe2;&#x9c;&#x93; Successfully clipped features to specified extent</source>
        <translation type="obsolete">指定範囲で正常にクリップされました。</translation>
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
        <translation type="obsolete">以下のレイヤがダウンロードされませんでした。</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="520"/>
        <source>Using single layer</source>
        <translation type="obsolete">単一レイヤを使用</translation>
    </message>
    <message>
        <location filename="../processing_provider/gsi_vt_dl_algorithm.py" line="522"/>
        <source>Merging {} layers</source>
        <translation type="obsolete">{} レイヤをマージしています。</translation>
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
