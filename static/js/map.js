let map;
let markers = [];
let heatmap;
let isHeatmapVisible = true;
let selectedPest = null;
let currentPoint = null;
let temperatureChart = null;
let contourLayers = [];
let gridLayer;
let contourLayer;
let heatLayer;
let legend;
let pests = []; // 害虫データを格納する配列

// DOMContentLoadedイベントで初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing map...');
    initMap();
});

// 最終更新日の表示
document.getElementById('last-update').textContent = new Date().toLocaleDateString();

function initializePestSelector() {
    const select = document.getElementById('pest-select');
    pests.forEach(pest => {
        const option = document.createElement('option');
        option.value = pest.id;
        option.textContent = pest.name;
        select.appendChild(option);
    });
    
    select.addEventListener('change', function() {
        selectedPest = pests.find(p => p.id === this.value) || null;
        updateMarkersColor();
        updateThresholdInfo();
        
        // 凡例をクリア
        const legend = document.querySelector('.legend');
        legend.innerHTML = '<h3>凡例</h3>';
        
        // 等高線を更新
        const temperatureData = markers.map(({ point }) => {
            const marker = point.marker;
            return {
                lat: point.lat,
                lon: point.lon,
                temperature: marker.options.fillColor === '#FF0000' ? 1 : 0
            };
        });
        generateContourLines(temperatureData);
    });
}

function loadGridPoints() {
    fetch('/api/grid_points')
        .then(response => response.json())
        .then(points => {
            const temperatureData = [];
            
            points.forEach(point => {
                // マーカーの作成（サイズをさらに小さく）
                const marker = L.circleMarker([point.lat, point.lon], {
                    radius: 1,
                    fillColor: '#FF0000',
                    color: '#FFFFFF',
                    weight: 0.5,
                    opacity: 0.3,
                    fillOpacity: 0.3
                }).addTo(map);
                
                marker.on('click', () => showTemperatureData(point));
                markers.push({ marker, point });
                
                // 温度データの取得
                fetch(`/api/temperature/${point.lat}/${point.lon}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.temperature !== undefined) {
                            // 温度データの追加
                            temperatureData.push({
                                lat: point.lat,
                                lon: point.lon,
                                temperature: data.temperature
                            });
                            
                            // マーカーの色を更新
                            const color = getTemperatureColor(data.temperature);
                            marker.setStyle({
                                fillColor: color
                            });
                        }
                    })
                    .catch(error => console.error('Error fetching temperature:', error));
            });
            
            // 等高線の生成
            if (selectedPest) {
                generateContourLines(temperatureData);
            }
        })
        .catch(error => console.error('Error loading grid points:', error));
}

function getTemperatureColor(temperature) {
    // 温度に応じて色を返す
    if (temperature < 0) {
        return '#0000FF';  // 青（氷点下）
    } else if (temperature < 10) {
        return '#00FFFF';  // 水色（冷たい）
    } else if (temperature < 20) {
        return '#00FF00';  // 緑（適温）
    } else if (temperature < 30) {
        return '#FFFF00';  // 黄（暖かい）
    } else {
        return '#FF0000';  // 赤（暑い）
    }
}

function showTemperatureData(point) {
    currentPoint = point;
    fetch(`/api/temperature/${point.lat}/${point.lon}`)
        .then(response => response.json())
        .then(data => {
            const info = document.getElementById('threshold-info');
            let thresholdInfo = '';
            
            if (selectedPest) {
                thresholdInfo = selectedPest.thresholds.map(threshold => {
                    const isAbove = data.temperature >= threshold.value;
                    return `<p>${threshold.label}: ${isAbove ? '達成' : '未達成'} (${threshold.value}℃)</p>`;
                }).join('');
            }
            
            info.innerHTML = `
                <p>地点情報</p>
                <p>緯度: ${point.lat}</p>
                <p>経度: ${point.lon}</p>
                <p>温度: ${data.temperature}℃</p>
                ${selectedPest ? `
                    <p>害虫: ${selectedPest.name}</p>
                    <p>成長ゼロ点: ${selectedPest.base_temp}℃</p>
                    ${thresholdInfo}
                ` : ''}
            `;
        })
        .catch(error => console.error('Error:', error));
}

function updateThresholdInfo() {
    const info = document.getElementById('threshold-info');
    if (selectedPest) {
        const thresholdInfo = selectedPest.thresholds.map(threshold => 
            `<p>${threshold.label}: ${threshold.value}℃日</p>`
        ).join('');
        
        info.innerHTML = `
            <p>害虫: ${selectedPest.name}</p>
            <p>成長ゼロ点: ${selectedPest.base_temp}℃</p>
            <p>${selectedPest.description}</p>
            <h4>閾値:</h4>
            ${thresholdInfo}
        `;
    } else {
        info.innerHTML = '<p>害虫を選択してください</p>';
    }
}

function updateTemperatureChart(data) {
    const ctx = document.getElementById('temperature-chart').getContext('2d');
    
    if (temperatureChart) {
        temperatureChart.destroy();
    }
    
    temperatureChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [data.date],
            datasets: [{
                label: '温度',
                data: [data.temperature],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateMarkersColor() {
    markers.forEach(({ marker, point }) => {
        fetch(`/api/temperature/${point.lat}/${point.lon}`)
            .then(response => response.json())
            .then(data => {
                if (data.temperature !== undefined) {
                    const color = getTemperatureColor(data.temperature);
                    marker.setStyle({
                        fillColor: color
                    });
                }
            })
            .catch(error => console.error('Error:', error));
    });
}

function toggleHeatmap() {
    isHeatmapVisible = !isHeatmapVisible;
    if (isHeatmapVisible) {
        map.addLayer(heatmap);
        document.getElementById('toggle-heatmap').textContent = 'ヒートマップを非表示';
    } else {
        map.removeLayer(heatmap);
        document.getElementById('toggle-heatmap').textContent = 'ヒートマップを表示';
    }
}

function updateContourLines(pest, temperatureData) {
    console.log('Updating contour lines with:', pest);
    console.log('Temperature data:', temperatureData);
    
    if (!pest || !temperatureData || temperatureData.length === 0) {
        console.error('Invalid data for contour lines');
        return;
    }
    
    // 既存の等値線をクリア
    contourLayer.clearLayers();
    
    try {
        // 温度データの準備
        const points = temperatureData.map(point => ({
            type: 'Feature',
            properties: {
                value: point.value
            },
            geometry: {
                type: 'Point',
                coordinates: [point.lon, point.lat]
            }
        }));
        
        const pointsCollection = {
            type: 'FeatureCollection',
            features: points
        };
        
        // 等値線の生成
        const breaks = [pest.threshold_temp];
        console.log('Using breaks:', breaks);
        
        // データの検証
        console.log('Points collection:', pointsCollection);
        console.log('First point:', pointsCollection.features[0]);
        
        // 等値線の生成
        const isolines = turf.isolines(pointsCollection, {
            breaks: breaks,
            zProperty: 'value'
        });
        
        console.log('Generated isolines:', isolines);
        
        // 等値線の表示
        if (isolines && isolines.features) {
            isolines.features.forEach(feature => {
                if (feature.geometry && feature.geometry.coordinates) {
                    const line = L.polyline(feature.geometry.coordinates.map(coord => [coord[1], coord[0]]), {
                        color: 'red',
                        weight: 2,
                        opacity: 0.8
                    }).addTo(contourLayer);
                }
            });
        }
        
        // 凡例の更新
        updateLegend(pest);
    } catch (error) {
        console.error('Error generating contour lines:', error);
        console.error('Error details:', {
            pest: pest,
            temperatureDataLength: temperatureData.length,
            firstPoint: temperatureData[0],
            breaks: [pest.threshold_temp]
        });
    }
}

function generateContourPoints(tempData, threshold) {
    if (!tempData || tempData.length === 0) return [];
    
    // グリッドポイントの座標を取得
    const points = tempData.map(point => ({
        lat: point.lat,
        lon: point.lon,
        value: point.value
    }));
    
    // 閾値以上のポイントを抽出
    const aboveThreshold = points.filter(p => p.value >= threshold);
    
    if (aboveThreshold.length === 0) return [];
    
    // 等値線のポイントを生成
    const contourPoints = [];
    const resolution = 0.02;
    
    // グリッドの範囲を計算
    const bounds = aboveThreshold.reduce((acc, point) => ({
        minLat: Math.min(acc.minLat, point.lat),
        maxLat: Math.max(acc.maxLat, point.lat),
        minLon: Math.min(acc.minLon, point.lon),
        maxLon: Math.max(acc.maxLon, point.lon)
    }), {
        minLat: Infinity,
        maxLat: -Infinity,
        minLon: Infinity,
        maxLon: -Infinity
    });
    
    // 補間グリッドを生成
    for (let lat = bounds.minLat; lat <= bounds.maxLat; lat += resolution) {
        for (let lon = bounds.minLon; lon <= bounds.maxLon; lon += resolution) {
            // 最近傍のポイントを探す
            const nearestPoints = aboveThreshold
                .map(p => ({
                    point: p,
                    distance: Math.sqrt(
                        Math.pow(p.lat - lat, 2) + 
                        Math.pow(p.lon - lon, 2)
                    )
                }))
                .sort((a, b) => a.distance - b.distance)
                .slice(0, 4);
            
            if (nearestPoints.length > 0) {
                // 逆距離加重法で値を補間
                const totalWeight = nearestPoints.reduce((sum, p) => sum + 1 / Math.pow(p.distance, 2), 0);
                const interpolatedValue = nearestPoints.reduce((sum, p) => 
                    sum + (p.point.value / Math.pow(p.distance, 2)), 0) / totalWeight;
                
                if (Math.abs(interpolatedValue - threshold) < 0.1) {
                    contourPoints.push([lat, lon]);
                }
            }
        }
    }
    
    // 等値線を滑らかにする
    const smoothedPoints = smoothContour(contourPoints);
    
    console.log('Generated contour points:', {
        threshold: threshold,
        pointsCount: points.length,
        aboveThresholdCount: aboveThreshold.length,
        contourPointsCount: smoothedPoints.length
    });
    
    return smoothedPoints;
}

function smoothContour(points) {
    if (points.length < 3) return points;
    
    // 移動平均で滑らかにする
    const smoothed = [];
    const windowSize = 5;
    
    // ポイントを時計回りに並べ替え
    const center = points.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1]], [0, 0]);
    center[0] /= points.length;
    center[1] /= points.length;
    
    const sortedPoints = points.sort((a, b) => {
        const angleA = Math.atan2(a[0] - center[0], a[1] - center[1]);
        const angleB = Math.atan2(b[0] - center[0], b[1] - center[1]);
        return angleA - angleB;
    });
    
    for (let i = 0; i < sortedPoints.length; i++) {
        const window = [];
        for (let j = -windowSize; j <= windowSize; j++) {
            const index = (i + j + sortedPoints.length) % sortedPoints.length;
            window.push(sortedPoints[index]);
        }
        
        // 重み付き移動平均
        const weights = window.map((_, idx) => 1 - Math.abs(idx - windowSize) / (windowSize + 1));
        const totalWeight = weights.reduce((sum, w) => sum + w, 0);
        
        const avgLat = window.reduce((sum, p, idx) => sum + p[0] * weights[idx], 0) / totalWeight;
        const avgLon = window.reduce((sum, p, idx) => sum + p[1] * weights[idx], 0) / totalWeight;
        
        smoothed.push([avgLat, avgLon]);
    }
    
    return smoothed;
}

function getThresholdColor(threshold) {
    // 閾値に応じて色を返す
    const colors = {
        '発生ピーク': '#00FF00',    // 緑
        '第二世代': '#FFFF00',      // 黄
        '第三世代以降': '#FF0000',  // 赤
        '幼虫': '#00FF00',         // 緑
        '成長羽化': '#FF0000'      // 赤
    };
    return colors[threshold.label] || '#FF0000';
}

function addToLegend(label, color) {
    const legendContent = document.getElementById('legend-content');
    if (!legendContent) {
        console.error('Legend content element not found');
        return;
    }
    
    const item = document.createElement('div');
    item.className = 'legend-item';
    
    const colorBox = document.createElement('div');
    colorBox.className = 'color-box';
    colorBox.style.backgroundColor = color;
    
    const labelText = document.createElement('span');
    labelText.textContent = label;
    
    item.appendChild(colorBox);
    item.appendChild(labelText);
    legendContent.appendChild(item);
    
    console.log('Added legend item:', { label, color });
}

// スタイルの追加
const style = document.createElement('style');
style.textContent = `
    .info {
        padding: 6px 8px;
        font: 14px/16px Arial, Helvetica, sans-serif;
        background: white;
        background: rgba(255,255,255,0.8);
        box-shadow: 0 0 15px rgba(0,0,0,0.2);
        border-radius: 5px;
    }
    .info h4 {
        margin: 0 0 5px;
        color: #777;
    }
    .legend {
        line-height: 18px;
        color: #555;
    }
    .legend-item {
        display: flex;
        align-items: center;
        margin: 2px 0;
    }
    .color-box {
        width: 18px;
        height: 18px;
        margin-right: 8px;
        border: 1px solid #999;
    }
`;
document.head.appendChild(style);

// 地図の初期化
function initMap() {
    console.log('Initializing map...');
    
    // 地図の初期化
    map = L.map('map').setView([35.6812, 139.7671], 8);
    
    // タイルレイヤーの追加
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // レイヤーの初期化
    gridLayer = L.layerGroup().addTo(map);
    contourLayer = L.layerGroup().addTo(map);
    
    // 凡例の初期化
    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'info legend');
        div.id = 'legend-content';
        return div;
    };
    legend.addTo(map);
    
    console.log('Map initialized');
    
    // 害虫データの取得
    fetchPests();
    
    // グリッドポイントの取得と表示
    fetchGridPoints();
}

// グリッドポイントの取得と表示
function fetchGridPoints() {
    console.log('Fetching grid points...');
    fetch('/api/grid_points')
        .then(response => response.json())
        .then(points => {
            console.log('Grid points loaded:', points.length);
            markers = [];
            
            // グリッドポイントの表示
            points.forEach(point => {
                const marker = L.circleMarker([point.lat, point.lon], {
                    radius: 3,
                    color: 'blue',
                    fillColor: 'blue',
                    fillOpacity: 0.5
                }).addTo(gridLayer);
                
                // マーカーをクリックしたときのイベント
                marker.on('click', () => {
                    console.log('Grid point clicked:', point);
                    showTemperatureData(point);
                });
                
                // マーカー情報を保存
                markers.push({
                    marker: marker,
                    point: point
                });
            });
        })
        .catch(error => console.error('Error fetching grid points:', error));
}

// 温度データの表示
function showTemperatureData(point) {
    const pointInfo = document.getElementById('point-info');
    if (!pointInfo) {
        console.error('Point info element not found');
        return;
    }
    
    fetch(`/api/temperature/${point.lat}/${point.lon}`)
        .then(response => response.json())
        .then(data => {
            pointInfo.innerHTML = `
                <p>緯度: ${point.lat}</p>
                <p>経度: ${point.lon}</p>
                <p>温度: ${data.temperature}℃</p>
            `;
        })
        .catch(error => {
            console.error('Error fetching temperature data:', error);
            pointInfo.innerHTML = '<p>温度データの取得に失敗しました</p>';
        });
}

// 害虫データの取得
function fetchPests() {
    console.log('Fetching pests...');
    fetch('/api/pests')
        .then(response => response.json())
        .then(pestsData => {
            console.log('Pests loaded:', pestsData);
            // グローバル変数に害虫データを格納
            pests = pestsData;
            
            const select = document.getElementById('pest-select');
            if (!select) {
                console.error('Pest select element not found');
                return;
            }
            
            // 害虫セレクターを初期化
            initializePestSelector();
            
            // 害虫選択のイベントリスナーを設定
            select.addEventListener('change', function() {
                const pestId = this.value;
                if (pestId) {
                    fetchPestData(pestId);
                } else {
                    // 選択がクリアされた場合
                    if (contourLayer) {
                        contourLayer.clearLayers();
                    }
                    const legendContent = document.getElementById('legend-content');
                    if (legendContent) {
                        legendContent.innerHTML = '';
                    }
                }
            });
        })
        .catch(error => console.error('Error loading pests:', error));
}

// 害虫データの取得と表示
function fetchPestData(pestId) {
    console.log('Fetching pest data for ID:', pestId);
    fetch(`/api/pests/${pestId}`)
        .then(response => response.json())
        .then(pest => {
            console.log('Pest data loaded:', pest);
            selectedPest = pest;
            const pestInfo = document.getElementById('pest-info');
            if (pestInfo) {
                const thresholdsHtml = pest.thresholds.map(threshold => 
                    `<p>${threshold.label}: ${threshold.value}℃日</p>`
                ).join('');
                
                pestInfo.innerHTML = `
                    <h3>${pest.name}</h3>
                    <p>${pest.description}</p>
                    <p>発育開始温度: ${pest.base_temp}℃</p>
                    <h4>閾値:</h4>
                    ${thresholdsHtml}
                `;
            }
            
            // 温度データの取得と等値線の更新
            fetchTemperatureData(pest);
        })
        .catch(error => console.error('Error loading pest data:', error));
}

// 温度データの取得と等値線の更新
function fetchTemperatureData(pest) {
    console.log('Fetching temperature data...');
    const temperatureData = [];
    const promises = markers.map(marker => {
        return fetch(`/api/temperature/${marker.point.lat}/${marker.point.lon}`)
            .then(response => response.json())
            .then(data => {
                if (data.temperature !== undefined) {
                    temperatureData.push({
                        lat: marker.point.lat,
                        lon: marker.point.lon,
                        value: data.temperature
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching temperature:', error);
            });
    });
    
    Promise.all(promises).then(() => {
        console.log('Temperature data loaded:', temperatureData);
        if (temperatureData.length > 0) {
            updateContourLines(pest, temperatureData);
        } else {
            console.error('No temperature data available');
        }
    });
}

// 凡例の作成
function createLegend() {
    // 既存の凡例を削除
    if (legend) {
        legend.remove();
    }
    
    // 新しい凡例を作成
    legend = L.control({ position: 'bottomright' });
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'info legend');
        div.innerHTML = '<h4>発生段階</h4><div id="legend-content"></div>';
        return div;
    };
    legend.addTo(map);
    
    console.log('Legend created');
}

// 凡例の更新
function updateLegend(pest) {
    const legendContent = document.getElementById('legend-content');
    if (!legendContent) {
        console.error('Legend content element not found');
        return;
    }
    
    const thresholdsHtml = pest.thresholds.map(threshold => 
        `<div class="legend-item">
            <span class="legend-color" style="background-color: ${threshold.color};"></span>
            <span>${threshold.label} (${threshold.value}℃日)</span>
        </div>`
    ).join('');
    
    legendContent.innerHTML = `
        <h4>${pest.name}</h4>
        <p>発育開始温度: ${pest.base_temp}℃</p>
        <p>${pest.description}</p>
        <h5>閾値:</h5>
        ${thresholdsHtml}
    `;
} 