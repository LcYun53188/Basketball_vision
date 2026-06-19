/* ==========================================================================
   SPORTVISION COACH - 前端交互逻辑
   WebSocket 双向流、网页录像控制、3D 轨迹映射与指标图形绘制
   ========================================================================== */

let activeAthleteId = null;
let activeSessionId = null;
let wsConn = null;
let isRecording = false;

// 摄像头与流捕获参数
let webcamStream = null;
let webcamTimer = null;
const FRAME_INTERVAL_MS = 60; // 约15-18帧每秒，平滑且不拥堵

// 3D 轨迹与人体投影记录
let trajectoryPath = []; // 包含最近 50 个点 [{x, y}]
let physicalTrajectoryPath = []; // 包含最近 50 个物理坐标点 [{x, y}]
let ballPhysicalTrajectoryPath = []; // 包含最近 50 个篮球物理投影点 [{x, y, z}]
let currentSkeletonWorld3D = null; // 存储 3D 投射人体关节点坐标

// 3D Three.js 查看器相关状态
let scene3D, camera3D, renderer3D, controls3D;
let playerTrajectoryLine3D, playerSkeleton3D, ballTrajectoryLine3D;
let is3DInitialized = false;
let currentViewMode = "2d"; // "2d" 或 "3d"

// 统计缓存
let totalAttempts = 0;
let totalGoals = 0;

// 1. 初始化入口
document.addEventListener("DOMContentLoaded", () => {
    loadAthletes();
    initDOMEvents();
    initCourtCanvas();
    initCalibrationModal();
});

// 2. DOM 事件绑定
function initDOMEvents() {
    // 运动员档案注册提交
    const regForm = document.getElementById("athlete-reg-form");
    regForm.addEventListener("submit", (e) => {
        e.preventDefault();
        registerAthlete();
    });

    // 切换 Tab (摄像头 vs 本地视频)
    const btnWebcam = document.getElementById("tab-webcam");
    const btnLocalVideo = document.getElementById("tab-local-video");
    const viewWebcam = document.getElementById("webcam-view");
    const viewLocalVideo = document.getElementById("local-video-view");

    btnWebcam.addEventListener("click", () => {
        btnWebcam.classList.add("active");
        btnLocalVideo.classList.remove("active");
        viewWebcam.classList.remove("hidden");
        viewLocalVideo.classList.add("hidden");
        stopLocalVideo();
        startWebcamStream();
    });

    btnLocalVideo.addEventListener("click", () => {
        btnLocalVideo.classList.add("active");
        btnWebcam.classList.remove("active");
        viewLocalVideo.classList.remove("hidden");
        viewWebcam.classList.add("hidden");
        stopWebcamStream();
    });

    // 本地视频分析加载
    const loadVideoBtn = document.getElementById("load-video-btn");
    loadVideoBtn.addEventListener("click", loadAndAnalyzeLocalVideo);

    // 对比开关变更重启 WebSocket 流以应用新配置
    const compareSwitch = document.getElementById("compare-switch");
    compareSwitch.addEventListener("change", () => {
        if (wsConn && wsConn.readyState === WebSocket.OPEN) {
            console.log("配置已变更，重新连接以应用比对库开关");
            restartActiveStream();
        }
    });

    // 服务端相机开关变更
    const serverCameraSwitch = document.getElementById("server-camera-switch");
    serverCameraSwitch.addEventListener("change", () => {
        console.log("摄像头数据源变更，重新连接");
        stopWebcamStream();
        startWebcamStream();
    });

    // 录像控制
    const recordBtn = document.getElementById("record-btn");
    recordBtn.addEventListener("click", toggleServerRecording);

    // AI 报告生成
    const genReportBtn = document.getElementById("gen-report-btn");
    genReportBtn.addEventListener("click", generateReport);

    // 导出报告
    const exportReportBtn = document.getElementById("export-report-btn");
    exportReportBtn.addEventListener("click", exportReport);

    // 切换 3D/2D 查看器
    document.getElementById("toggle-view-2d").addEventListener("click", () => {
        document.getElementById("toggle-view-2d").classList.add("active");
        document.getElementById("toggle-view-3d").classList.remove("active");
        document.getElementById("court-canvas").classList.remove("hidden");
        document.getElementById("court-3d-canvas-container").classList.add("hidden");
        document.getElementById("court-view-info").textContent = "三维物理世界投影基准：底线中点为原点 (0, 0)。红点代表足底实时位置，带有运动拖尾。";
        currentViewMode = "2d";
    });

    document.getElementById("toggle-view-3d").addEventListener("click", () => {
        document.getElementById("toggle-view-2d").classList.remove("active");
        document.getElementById("toggle-view-3d").classList.add("active");
        document.getElementById("court-canvas").classList.add("hidden");
        document.getElementById("court-3d-canvas-container").classList.remove("hidden");
        document.getElementById("court-view-info").textContent = "WebGL 交互式 3D 球场：按住鼠标左键拖拽可旋转视角，鼠标右键拖拽可平移，滚轮缩放。";
        currentViewMode = "3d";
        init3DCourt();
        update3DView();
    });
}

// 3. API 请求：运动员模块
async function loadAthletes() {
    try {
        const res = await fetch("/api/v1/athletes");
        const data = await res.json();
        const ul = document.getElementById("athletes-ul");
        ul.innerHTML = "";

        if (data.length === 0) {
            ul.innerHTML = `<li class="player-subtitle">暂无已注册球员</li>`;
            return;
        }

        data.forEach(p => {
            const li = document.createElement("li");
            li.dataset.id = p.id;
            li.className = p.id === activeAthleteId ? "active" : "";
            
            li.innerHTML = `
                <div class="player-info">
                    <span class="player-title">${p.name} (${p.gender === 'male' ? '男' : '女'})</span>
                    <span class="player-subtitle">场上位置: ${p.position} | 年龄: ${p.age}岁</span>
                </div>
                <span class="player-badge">${p.dominant_hand === 'right' ? '右手' : '左手'}</span>
            `;
            li.addEventListener("click", () => selectAthlete(p.id));
            ul.appendChild(li);
        });
    } catch (e) {
        console.error("加载球员列表失败", e);
    }
}

async function registerAthlete() {
    const name = document.getElementById("athlete-name").value;
    const gender = document.getElementById("athlete-gender").value;
    const age = parseInt(document.getElementById("athlete-age").value);
    const position = document.getElementById("athlete-position").value;
    const hand = document.getElementById("athlete-hand").value;

    try {
        const res = await fetch("/api/v1/athletes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name, gender, age, position, dominant_hand: hand
            })
        });

        if (res.ok) {
            document.getElementById("athlete-reg-form").reset();
            await loadAthletes();
        }
    } catch (e) {
        console.error("登记球员失败", e);
    }
}

function selectAthlete(id) {
    activeAthleteId = id;
    document.querySelectorAll("#athletes-ul li").forEach(li => {
        li.classList.toggle("active", parseInt(li.dataset.id) === id);
    });
    console.log(`已选择当前球员 ID: ${id}`);
    
    // 初始化新的训练会话
    createNewSession("camera");
}

// 4. API 请求：训练会话模块
async function createNewSession(sourceType) {
    if (!activeAthleteId) {
        console.warn("请先选择一位球员进行会话绑定");
        return;
    }

    try {
        // 创建会话，为测试默认注入一段预设标定参数数据（NBA 罚球线和篮架标定）
        const calibData = {
            "H": [
                [0.05, -0.12, 1.2],
                [0.18, 0.08, -0.4],
                [0.0, 0.0, 1.0]
            ],
            "description": "默认标定单应性参数"
        };

        const res = await fetch("/api/v1/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                athlete_id: activeAthleteId,
                source_type: sourceType,
                calibration_data: calibData,
                notes: `由 WebUI 触发的 ${sourceType} 训练分析`
            })
        });

        const data = await res.json();
        activeSessionId = data.id;
        console.log(`会话创建成功 ID: ${activeSessionId}`);

        // 重置进球统计与轨迹数据
        totalAttempts = 0;
        totalGoals = 0;
        trajectoryPath = [];
        physicalTrajectoryPath = [];
        ballPhysicalTrajectoryPath = [];
        currentSkeletonWorld3D = null;
        document.getElementById("stat-goals").textContent = "0";
        document.getElementById("stat-attempts").textContent = "0";
        document.getElementById("stat-pct").textContent = "0%";
        document.getElementById("goal-ticker").innerHTML = `<div class="ticker-empty">暂无进球数据记录</div>`;
        document.getElementById("report-output-box").classList.add("hidden");

        // 如果选择摄像头，立即建立 WebSocket 连接
        if (sourceType === "camera") {
            restartActiveStream();
        }
    } catch (e) {
        console.error("创建会话失败", e);
    }
}

// 5. 视频推流控制 (Webcam Stream via WS)
// 5. 视频推流控制 (Webcam Stream via WS)
function stopWebcamStream() {
    if (webcamTimer) {
        clearInterval(webcamTimer);
        webcamTimer = null;
    }
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    if (wsConn) {
        wsConn.close();
        wsConn = null;
    }
    document.getElementById("conn-status-text").textContent = "系统就绪";
    
    // 恢复视频并隐藏 fallback 图片
    document.getElementById("webcam-element").classList.remove("hidden");
    document.getElementById("webcam-fallback-img").classList.add("hidden");
}

async function startWebcamStream() {
    stopWebcamStream();
    if (!activeSessionId) {
        console.warn("未关联训练会话，正在尝试自动匹配默认球员会话...");
        if (!activeAthleteId) {
            alert("提示: 请先在左侧选择或登记一名球员！");
            return;
        }
        await createNewSession("camera");
        return;
    }

    const videoEl = document.getElementById("webcam-element");
    const fallbackImg = document.getElementById("webcam-fallback-img");
    const useServerCam = document.getElementById("server-camera-switch").checked;

    if (useServerCam) {
        videoEl.classList.add("hidden");
        fallbackImg.classList.remove("hidden");
        // 开启 WebSocket 数据流 (使用服务端相机不需要 getUserMedia)
        connectWebSocket();
        return;
    } else {
        videoEl.classList.remove("hidden");
        fallbackImg.classList.add("hidden");
    }

    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, frameRate: { ideal: 25 } },
            audio: false
        });
        videoEl.srcObject = webcamStream;
        
        // 开启 WebSocket 数据流
        connectWebSocket();
    } catch (e) {
        console.error("无法启动本地摄像头", e);
        alert("本地摄像头访问受限，您可以切换为 [使用服务端相机(OpenCV)] 或 [本地视频分析]！");
    }
}

function restartActiveStream() {
    if (wsConn) {
        wsConn.close();
        wsConn = null;
    }
    connectWebSocket();
}

// WebSocket 核心连接与推帧逻辑
function connectWebSocket() {
    if (!activeSessionId) return;

    const compareActive = document.getElementById("compare-switch").checked;
    const useServerCam = document.getElementById("server-camera-switch").checked;
    const wsUrl = `ws://${window.location.host}/api/v1/sessions/ws/${activeSessionId}?compare_with_reference=${compareActive}&record=${isRecording}&use_server_camera=${useServerCam}&camera_index=0`;
    
    wsConn = new WebSocket(wsUrl);
    document.getElementById("conn-status-text").textContent = "正在连接 WebSocket...";

    wsConn.onopen = () => {
        document.getElementById("conn-status-text").textContent = "实时连接中";
        document.getElementById("conn-status-text").parentElement.querySelector('.status-dot').className = 'status-dot green';
        
        // 开始捕获帧像素，转换为 base64 发送 (仅在未使用服务端本地相机时)
        if (!useServerCam) {
            startFrameCaptureLoop();
        }
    };

    wsConn.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        handleWSResponse(payload);
    };

    wsConn.onclose = () => {
        document.getElementById("conn-status-text").textContent = "流连接断开";
        document.getElementById("conn-status-text").parentElement.querySelector('.status-dot').className = 'status-dot orange';
    };
}

function startFrameCaptureLoop() {
    if (webcamTimer) clearInterval(webcamTimer);

    const videoEl = document.getElementById("tab-webcam").classList.contains("active") 
        ? document.getElementById("webcam-element")
        : document.getElementById("playback-video-element");

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    let frameIdx = 0;

    webcamTimer = setInterval(() => {
        if (!wsConn || wsConn.readyState !== WebSocket.OPEN) return;
        
        // 只有在视频有数据且没有暂停时才推送帧
        if (videoEl.paused || videoEl.ended) return;

        canvas.width = videoEl.videoWidth || 640;
        canvas.height = videoEl.videoHeight || 480;
        
        ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
        
        // 压缩成 JPEG 格式以降低带宽消耗
        const dataUrl = canvas.toDataURL("image/jpeg", 0.65);

        const msg = {
            frame_index: frameIdx++,
            timestamp_ms: videoEl.currentTime ? videoEl.currentTime * 1000 : Date.now(),
            frame: dataUrl
        };

        wsConn.send(JSON.stringify(msg));
    }, FRAME_INTERVAL_MS);
}

// 6. 接收并处理推演结果（动作、比对、进球、3D投影）
function handleWSResponse(data) {
    // A. 绘制人体骨骼关键点覆盖图
    // 如果存在服务端直接下发的图像，更新 fallback img src
    if (data.frame) {
        document.getElementById("webcam-fallback-img").src = data.frame;
    }

    drawSkeletonOverlay(data.keypoints, data.ball_bbox, data.hoop_bbox);

    // B. 显示动作检测状态
    const statusOverlay = document.getElementById("overlay-action");
    statusOverlay.textContent = `状态: ${data.action_type.toUpperCase()}`;

    // C. 3D 球场投影点绘制与轨迹添加
    currentSkeletonWorld3D = data.skeleton_world_3d;
    if (data.feet_world_3d) {
        // [X, Y, Z] 投影
        addTrajectoryPoint(data.feet_world_3d[0], data.feet_world_3d[1]);
    } else {
        renderCourtFrame();
    }
    if (data.ball_world_3d) {
        addBallProjectionPoint(data.ball_world_3d[0], data.ball_world_3d[1], data.ball_world_3d[2] || 0);
    }

    // D. 物理特征指标比对反馈
    updateMetricsTelemetry(data.comparisons);

    // E. 进球事件状态反馈
    if (data.goal_event) {
        logGoalEvent(data.goal_event);
    }
}

// 绘制骨架和目标框
function drawSkeletonOverlay(keypoints, ballBbox, hoopBbox) {
    const canvas = document.getElementById("skeleton-canvas");
    const ctx = canvas.getContext("2d");
    
    // 自适应大小
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!keypoints || keypoints.length === 0) return;

    // 绘制关节连接骨骼
    const connections = [
        ["left_shoulder", "right_shoulder"],
        ["left_shoulder", "left_elbow"], ["left_elbow", "left_wrist"],
        ["right_shoulder", "right_elbow"], ["right_elbow", "right_wrist"],
        ["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"],
        ["left_hip", "right_hip"],
        ["left_hip", "left_knee"], ["left_knee", "left_ankle"],
        ["right_hip", "right_knee"], ["right_knee", "right_ankle"]
    ];

    ctx.strokeStyle = "rgba(0, 229, 255, 0.7)";
    ctx.lineWidth = 3;

    connections.forEach(([p1, p2]) => {
        const kp1 = keypoints.find(k => k.name === p1);
        const kp2 = keypoints.find(k => k.name === p2);
        if (kp1 && kp2 && kp1.visibility > 0.4 && kp2.visibility > 0.4) {
            ctx.beginPath();
            ctx.moveTo(kp1.x * canvas.width, kp1.y * canvas.height);
            ctx.lineTo(kp2.x * canvas.width, kp2.y * canvas.height);
            ctx.stroke();
        }
    });

    // 绘制关键点
    keypoints.forEach(kp => {
        if (kp.visibility > 0.4) {
            ctx.beginPath();
            ctx.arc(kp.x * canvas.width, kp.y * canvas.height, 4, 0, 2 * Math.PI);
            ctx.fillStyle = kp.name.includes("wrist") || kp.name.includes("ankle") ? "#E040FB" : "#00E676";
            ctx.fill();
        }
    });

    // 绘制篮球与篮筐定位框
    if (ballBbox) {
        ctx.strokeStyle = "#FF8000";
        ctx.lineWidth = 2;
        ctx.beginPath();
        // 假定输入的 bbox 比例正常
        ctx.rect(ballBbox[0], ballBbox[1], ballBbox[2] - ballBbox[0], ballBbox[3] - ballBbox[1]);
        ctx.stroke();
        ctx.fillStyle = "#FF8000";
        ctx.font = "10px sans-serif";
        ctx.fillText("BALL", ballBbox[0], ballBbox[1] - 4);
    }

    if (hoopBbox) {
        ctx.strokeStyle = "#FF3D00";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.rect(hoopBbox[0], hoopBbox[1], hoopBbox[2] - hoopBbox[0], hoopBbox[3] - hoopBbox[1]);
        ctx.stroke();
    }
}

// 7. 三维球场渲染与投影绘制
let courtCanvas = null;
let courtCtx = null;

function initCourtCanvas() {
    courtCanvas = document.getElementById("court-canvas");
    courtCtx = courtCanvas.getContext("2d");
    
    // 画布尺寸
    courtCanvas.width = 600;
    courtCanvas.height = 220;
    
    drawBasketballCourt();
}

function drawBasketballCourt() {
    const ctx = courtCtx;
    const w = courtCanvas.width;
    const h = courtCanvas.height;

    ctx.fillStyle = "#0A0D15";
    ctx.fillRect(0, 0, w, h);

    // 画线颜色
    ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = 2;

    // 1. 底线与边线 (物理：长约 14米截面，底线 15.24m)
    // 映射关系：底线在 Y=0 (画布 Y 轴靠上)，Y轴向外延伸。
    ctx.beginPath();
    ctx.rect(50, 10, w - 100, h - 20);
    ctx.stroke();

    // 2. 罚球区 (Key area)
    ctx.beginPath();
    ctx.rect(w/2 - 50, 10, 100, 70);
    ctx.stroke();

    // 3. 罚球线圆弧
    ctx.beginPath();
    ctx.arc(w/2, 80, 50, 0, Math.PI);
    ctx.stroke();

    // 4. 三分线
    ctx.beginPath();
    ctx.arc(w/2, 10, 140, 0, Math.PI);
    ctx.stroke();
}

function addTrajectoryPoint(x, y) {
    // x, y 为物理世界 3D 坐标米。NBA 标准底线 15.24m 宽，X 为 [-7.62, 7.62], Y 长度。
    // 映射到画布 [50, w - 50]
    const w = courtCanvas.width;
    const h = courtCanvas.height;

    const screenX = w / 2 + (x / 7.62) * (w / 2 - 50);
    const screenY = 10 + (y / 14.0) * (h - 20); // 假定纵向拉伸

    trajectoryPath.push({ x: screenX, y: screenY });
    if (trajectoryPath.length > 50) {
        trajectoryPath.shift();
    }

    // 存储物理轨迹点用于 3D 视图
    physicalTrajectoryPath.push({ x: x, y: y });
    if (physicalTrajectoryPath.length > 50) {
        physicalTrajectoryPath.shift();
    }

    renderCourtFrame();
}

function addBallProjectionPoint(x, y, z) {
    ballPhysicalTrajectoryPath.push({ x: x, y: y, z: z });
    if (ballPhysicalTrajectoryPath.length > 50) {
        ballPhysicalTrajectoryPath.shift();
    }
    if (currentViewMode === "3d") {
        update3DView();
    }
}

function renderCourtFrame() {
    drawBasketballCourt();
    
    const ctx = courtCtx;
    if (trajectoryPath.length > 0) {
        // 绘制足底运动轨迹连线
        ctx.strokeStyle = "rgba(138, 43, 226, 0.4)";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(trajectoryPath[0].x, trajectoryPath[0].y);
        for (let i = 1; i < trajectoryPath.length; i++) {
            ctx.lineTo(trajectoryPath[i].x, trajectoryPath[i].y);
        }
        ctx.stroke();

        // 绘制当前足底实时位置红点与脉冲光环
        const current = trajectoryPath[trajectoryPath.length - 1];
        ctx.fillStyle = "#FF1744";
        ctx.beginPath();
        ctx.arc(current.x, current.y, 6, 0, 2 * Math.PI);
        ctx.fill();

        ctx.strokeStyle = "rgba(255, 23, 68, 0.5)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(current.x, current.y, 12, 0, 2 * Math.PI);
        ctx.stroke();
    }

    if (currentSkeletonWorld3D) {
        drawSkeletonOnCourt(currentSkeletonWorld3D);
    }

    if (currentViewMode === "3d") {
        update3DView();
    }
}

function drawSkeletonOnCourt(skeleton) {
    if (!skeleton) return;

    const w = courtCanvas.width;
    const h = courtCanvas.height;
    const ctx = courtCtx;

    // 高度缩放比例 (将垂直高度 Z 米转换为 Canvas 上的 y 轴偏移像素)
    const zScale = 15;

    // 将 3D 实境点映射到 2.5D Canvas 坐标系
    function project3D(pt) {
        const x = pt[0];
        const y = pt[1];
        const z = pt[2];
        const screenX = w / 2 + (x / 7.62) * (w / 2 - 50);
        const screenY = 10 + (y / 14.0) * (h - 20) - z * zScale;
        return { x: screenX, y: screenY };
    }

    const connections = [
        ["left_shoulder", "right_shoulder"],
        ["left_shoulder", "left_elbow"], ["left_elbow", "left_wrist"],
        ["right_shoulder", "right_elbow"], ["right_elbow", "right_wrist"],
        ["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"],
        ["left_hip", "right_hip"],
        ["left_hip", "left_knee"], ["left_knee", "left_ankle"],
        ["right_hip", "right_knee"], ["right_knee", "right_ankle"]
    ];

    // 绘制骨架线
    ctx.strokeStyle = "rgba(0, 229, 255, 0.85)";
    ctx.lineWidth = 2.5;
    connections.forEach(([p1, p2]) => {
        const pt1 = skeleton[p1];
        const pt2 = skeleton[p2];
        if (pt1 && pt2) {
            const s1 = project3D(pt1);
            const s2 = project3D(pt2);
            ctx.beginPath();
            ctx.moveTo(s1.x, s1.y);
            ctx.lineTo(s2.x, s2.y);
            ctx.stroke();
        }
    });

    // 绘制关节圆点
    for (const name in skeleton) {
        const pt = skeleton[name];
        const s = project3D(pt);
        ctx.beginPath();
        ctx.arc(s.x, s.y, 3.5, 0, 2 * Math.PI);
        ctx.fillStyle = name.includes("wrist") || name.includes("ankle") ? "#E040FB" : "#00E676";
        ctx.fill();
    }
}

// 8. 数据比对反馈仪表盘
function updateMetricsTelemetry(comparisons) {
    if (!comparisons) {
        // 如果未开启比对，只进行指标常规展示，重置为灰色
        document.querySelectorAll(".metric-row").forEach(row => {
            row.className = "metric-row";
        });
        return;
    }

    comparisons.forEach(c => {
        let barId, valId, rowEl;
        if (c.name === "elbow_angle_deg") {
            barId = "bar-elbow";
            valId = "val-elbow";
            rowEl = document.getElementById(barId).closest(".metric-row");
        } else if (c.name === "knee_angle_deg") {
            barId = "bar-knee";
            valId = "val-knee";
            rowEl = document.getElementById(barId).closest(".metric-row");
        } else if (c.name === "torso_lean_deg") {
            barId = "bar-torso";
            valId = "val-torso";
            rowEl = document.getElementById(barId).closest(".metric-row");
        }

        if (barId && valId) {
            const bar = document.getElementById(barId);
            const val = document.getElementById(valId);
            
            val.textContent = c.value !== null ? `${Math.round(c.value)}°` : "--°";

            // 设置填充进度比例
            let pct = 0;
            if (c.name === "torso_lean_deg") pct = (c.value / 45) * 100;
            else pct = (c.value / 180) * 100;
            bar.style.width = `${Math.min(100, Math.max(0, pct))}%`;

            // 应用状态颜色
            rowEl.className = `metric-row ${c.status}`; // ok, low, high, missing
        }
    });
}

// 9. 进球监测日志
function logGoalEvent(goal) {
    totalAttempts += 1;
    totalGoals += 1; // 仅当返回有效进球事件时

    document.getElementById("stat-goals").textContent = totalGoals;
    document.getElementById("stat-attempts").textContent = totalAttempts;
    document.getElementById("stat-pct").textContent = `${Math.round((totalGoals / totalAttempts) * 100)}%`;

    const ticker = document.getElementById("goal-ticker");
    const empty = ticker.querySelector(".ticker-empty");
    if (empty) empty.remove();

    const item = document.createElement("div");
    item.className = `ticker-item ${goal.goal_type}`;
    item.innerHTML = `
        <span>🎯 进球判定成功! [${goal.goal_type.toUpperCase()}]</span>
        <span>帧 #${goal.frame_index}</span>
    `;
    ticker.prepend(item);
}

// 10. 服务端录屏开启/暂停
function toggleServerRecording() {
    if (!activeSessionId) {
        alert("请先启动实时推流会话再进行录制！");
        return;
    }

    const btn = document.getElementById("record-btn");
    isRecording = !isRecording;

    if (isRecording) {
        btn.classList.add("recording");
        btn.innerHTML = `<span class="record-dot"></span> 正在录制...`;
        console.log("开启服务端无损录像");
    } else {
        btn.classList.remove("recording");
        btn.innerHTML = `<span class="record-dot"></span> 开启录制`;
        console.log("停止服务端录像并归档");
    }

    // 重启 WebSocket 连接以携带新录屏标志参数
    restartActiveStream();
}

// 11. 本地视频播放选项与分析实现
function stopLocalVideo() {
    const video = document.getElementById("playback-video-element");
    video.pause();
    video.src = "";
    document.getElementById("analysis-status").textContent = "等待载入...";
    stopWebcamStream();
}

async function loadAndAnalyzeLocalVideo() {
    if (!activeAthleteId) {
        alert("请先选择一位球员绑定本次视频会话！");
        return;
    }

    const fileInput = document.getElementById("local-video-file");
    const videoFile = fileInput.files && fileInput.files[0];
    if (!videoFile) {
        alert("请选择一个本地视频文件！");
        return;
    }

    const loadBtn = document.getElementById("load-video-btn");
    loadBtn.disabled = true;
    document.getElementById("analysis-status").textContent = "正在上传视频...";
    
    // 1. 创建会话
    await createNewSession("video");

    try {
        // 2. 上传本地文件，后端保存媒体资源并启动离线分析
        const formData = new FormData();
        formData.append("file", videoFile);
        const uploadRes = await fetch(`/api/v1/sessions/${activeSessionId}/upload-video`, {
            method: "POST",
            body: formData
        });

        if (!uploadRes.ok) {
            const err = await uploadRes.json().catch(() => ({}));
            throw new Error(err.detail || "视频上传失败");
        }

        await uploadRes.json();

        // 3. 绑定服务端回放地址，播放时同步走 WebSocket 逐帧投影
        const video = document.getElementById("playback-video-element");
        video.src = `/api/v1/sessions/${activeSessionId}/video/playback`;
        video.load();

        document.getElementById("analysis-status").textContent = "上传完成，离线分析已开始。";

        connectWebSocket();
    } catch (e) {
        console.error("加载本地视频失败", e);
        document.getElementById("analysis-status").textContent = e.message || "加载失败";
    } finally {
        loadBtn.disabled = false;
    }
}

// 12. AI 教练评估报告
let generatedReportId = null;

async function generateReport() {
    if (!activeSessionId) {
        alert("请选择或进行一次训练会话后再生成报告！");
        return;
    }

    document.getElementById("gen-report-btn").textContent = "正在分析生成中...";

    try {
        const res = await fetch("/api/v1/reports/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: activeSessionId })
        });
        const data = await res.json();
        
        generatedReportId = data.id;

        // 转换为简易 html 展示
        let html = data.report_text
            .replace(/### (.*)/g, "<h3>$1</h3>")
            .replace(/#### (.*)/g, "<h3>$1</h3>")
            .replace(/\*\*(.*)\*\*/g, "<strong>$1</strong>")
            .replace(/\n/g, "<p>");

        document.getElementById("report-text-div").innerHTML = html;
        document.getElementById("report-output-box").classList.remove("hidden");
    } catch (e) {
        console.error("生成报告失败", e);
    } finally {
        document.getElementById("gen-report-btn").textContent = "生成智能分析报告";
    }
}

function exportReport() {
    if (!generatedReportId) return;
    // 直接浏览器触发下载
    window.location.href = `/api/v1/reports/${generatedReportId}/export`;
}

// 13. 相机标定交互向导实现
let clickedCalibPoints = [];
const CALIB_STEP_NAMES = [
    "底线左侧角点",
    "底线右侧角点",
    "左侧罚球点",
    "右侧罚球点",
    "篮板左下角",
    "篮板右下角",
    "篮板右上角",
    "篮板左上角"
];

function initCalibrationModal() {
    const startBtn = document.getElementById("start-calibrate-btn");
    const modal = document.getElementById("calibration-modal");
    const cancelBtn = document.getElementById("cancel-calib-btn");
    const resetBtn = document.getElementById("reset-calib-btn");
    const confirmBtn = document.getElementById("confirm-calib-btn");
    const canvas = document.getElementById("calibration-canvas");
    const ctx = canvas.getContext("2d");

    let originalImgData = null;
    let originalWidth = 640;
    let originalHeight = 480;

    startBtn.addEventListener("click", () => {
        if (!activeSessionId) {
            alert("请先选择球员并启动会话，方可进行相机标定！");
            return;
        }

        // 获取当前视频画面源
        let sourceEl = null;
        const webcamTabActive = document.getElementById("tab-webcam").classList.contains("active");
        if (webcamTabActive) {
            const useServerCam = document.getElementById("server-camera-switch").checked;
            if (useServerCam) {
                sourceEl = document.getElementById("webcam-fallback-img");
            } else {
                sourceEl = document.getElementById("webcam-element");
            }
        } else {
            sourceEl = document.getElementById("playback-video-element");
        }

        if (!sourceEl || (sourceEl.tagName === "VIDEO" && sourceEl.videoWidth === 0) || (sourceEl.tagName === "IMG" && !sourceEl.src)) {
            alert("当前无可用视频流帧，请先开启摄像头或播放视频！");
            return;
        }

        // 初始化 Canvas 宽高
        originalWidth = sourceEl.videoWidth || sourceEl.naturalWidth || 640;
        originalHeight = sourceEl.videoHeight || sourceEl.naturalHeight || 480;
        
        // 限制在工作区展示的大小 (比如 640x480)
        canvas.width = 640;
        canvas.height = 480;

        // 绘制冻结帧
        ctx.drawImage(sourceEl, 0, 0, canvas.width, canvas.height);
        originalImgData = ctx.getImageData(0, 0, canvas.width, canvas.height);

        // 重置标定数据
        clickedCalibPoints = [];
        updateCalibStepsUI();
        confirmBtn.disabled = true;

        modal.classList.remove("hidden");
    });

    cancelBtn.addEventListener("click", () => {
        modal.classList.add("hidden");
    });

    resetBtn.addEventListener("click", () => {
        if (originalImgData) {
            ctx.putImageData(originalImgData, 0, 0);
        }
        clickedCalibPoints = [];
        updateCalibStepsUI();
        confirmBtn.disabled = true;
    });

    canvas.addEventListener("click", (e) => {
        if (clickedCalibPoints.length >= 8) return;

        const rect = canvas.getBoundingClientRect();
        // 映射为 Canvas 内的像素坐标 (640x480 空间)
        const clickX = ((e.clientX - rect.left) / rect.width) * canvas.width;
        const clickY = ((e.clientY - rect.top) / rect.height) * canvas.height;

        // 缩放到原视频真实分辨率下，保证 PnP 解算精度
        const scaleX = originalWidth / canvas.width;
        const scaleY = originalHeight / canvas.height;
        const realX = clickX * scaleX;
        const realY = clickY * scaleY;

        clickedCalibPoints.push([realX, realY]);

        // 在 Canvas 绘制圆点和字样
        ctx.fillStyle = "#FF1744";
        ctx.beginPath();
        ctx.arc(clickX, clickY, 5, 0, 2 * Math.PI);
        ctx.fill();

        ctx.fillStyle = "#00E5FF";
        ctx.font = "14px Outfit, sans-serif";
        ctx.fillText(`P${clickedCalibPoints.length}`, clickX + 8, clickY - 8);

        updateCalibStepsUI();

        if (clickedCalibPoints.length === 8) {
            confirmBtn.disabled = false;
        }
    });

    confirmBtn.addEventListener("click", async () => {
        if (clickedCalibPoints.length !== 8) return;

        confirmBtn.textContent = "正在提交...";
        confirmBtn.disabled = true;

        try {
            const res = await fetch(`/api/v1/sessions/${activeSessionId}/calibrate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    points: clickedCalibPoints,
                    width: originalWidth,
                    height: originalHeight
                })
            });

            if (res.ok) {
                alert("相机内外参与单应性矩阵标定成功！3D 投影映射已自动更新。");
                modal.classList.add("hidden");
                // 重启流以获取最新标定数据
                restartActiveStream();
            } else {
                const err = await res.json();
                alert(`标定计算失败: ${err.detail || "算法未收敛，请确保 8 个点点击顺序和位置正确"}`);
            }
        } catch (e) {
            console.error("提交标定请求失败", e);
            alert("提交标定失败，请检查网络连接");
        } finally {
            confirmBtn.textContent = "确认标定";
            confirmBtn.disabled = false;
        }
    });
}

function updateCalibStepsUI() {
    const listItems = document.querySelectorAll("#calibration-steps li");
    const currentStep = clickedCalibPoints.length;
    listItems.forEach((li, index) => {
        if (index === currentStep) {
            li.className = "active";
        } else if (index < currentStep) {
            li.className = "done";
        } else {
            li.className = "";
        }
    });
}

// ==========================================================================
// WebGL 3D 三维球场查看器实现 (Three.js)
// ==========================================================================
function init3DCourt() {
    if (is3DInitialized) return;

    const container = document.getElementById("court-3d-canvas-container");
    const width = container.clientWidth;
    const height = container.clientHeight || 260;

    // 1. 创建场景与渲染器
    scene3D = new THREE.Scene();
    scene3D.background = new THREE.Color(0x0a0f19);

    camera3D = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera3D.position.set(0, 12, 18);

    renderer3D = new THREE.WebGLRenderer({ antialias: true });
    renderer3D.setSize(width, height);
    renderer3D.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer3D.domElement);

    // 2. 轨道控制器
    controls3D = new THREE.OrbitControls(camera3D, renderer3D.domElement);
    controls3D.enableDamping = true;
    controls3D.dampingFactor = 0.05;
    controls3D.maxPolarAngle = Math.PI / 2 - 0.05;

    // 3. 光照
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene3D.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(5, 15, 5);
    scene3D.add(dirLight);

    // 4. 绘制半场地面 (宽15.24m, 长14.0m)
    const courtGeo = new THREE.PlaneGeometry(15.24, 14.0);
    const courtMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.8, side: THREE.DoubleSide });
    const courtMesh = new THREE.Mesh(courtGeo, courtMat);
    courtMesh.rotation.x = -Math.PI / 2;
    courtMesh.position.set(0, 0, 7.0);
    scene3D.add(courtMesh);

    // 绘制白线
    const linesMaterial = new THREE.LineBasicMaterial({ color: 0xffffff });
    
    // 边界框
    const boundaryPoints = [
        new THREE.Vector3(-7.62, 0.01, 0),
        new THREE.Vector3(7.62, 0.01, 0),
        new THREE.Vector3(7.62, 0.01, 14.0),
        new THREE.Vector3(-7.62, 0.01, 14.0),
        new THREE.Vector3(-7.62, 0.01, 0)
    ];
    const boundaryGeo = new THREE.BufferGeometry().setFromPoints(boundaryPoints);
    const boundaryLine = new THREE.Line(boundaryGeo, linesMaterial);
    scene3D.add(boundaryLine);

    // 罚球线及限制区 (Y=5.79m, 宽4.88m)
    const ftPoints = [
        new THREE.Vector3(-2.44, 0.01, 0),
        new THREE.Vector3(-2.44, 0.01, 5.79),
        new THREE.Vector3(2.44, 0.01, 5.79),
        new THREE.Vector3(2.44, 0.01, 0)
    ];
    const ftGeo = new THREE.BufferGeometry().setFromPoints(ftPoints);
    const ftLine = new THREE.Line(ftGeo, linesMaterial);
    scene3D.add(ftLine);

    // 罚球弧 (Y=5.79m, 半径1.80m)
    const arcPoints = [];
    for (let theta = 0; theta <= Math.PI; theta += 0.1) {
        arcPoints.push(new THREE.Vector3(1.80 * Math.cos(theta), 0.01, 5.79 + 1.80 * Math.sin(theta)));
    }
    const arcGeo = new THREE.BufferGeometry().setFromPoints(arcPoints);
    const arcLine = new THREE.Line(arcGeo, linesMaterial);
    scene3D.add(arcLine);

    // 三分弧线 (半径7.24m, 篮筐圆心在 0, 1.40m)
    const threePtPoints = [
        new THREE.Vector3(-6.71, 0.01, 0),
        new THREE.Vector3(-6.71, 0.01, 4.26)
    ];
    const angleStart = Math.asin((4.26 - 1.40) / 7.24);
    for (let theta = angleStart; theta <= Math.PI - angleStart; theta += 0.05) {
        threePtPoints.push(new THREE.Vector3(7.24 * Math.cos(Math.PI - theta), 0.01, 1.40 + 7.24 * Math.sin(Math.PI - theta)));
    }
    threePtPoints.push(new THREE.Vector3(6.71, 0.01, 4.26));
    threePtPoints.push(new THREE.Vector3(6.71, 0.01, 0));
    
    const threePtGeo = new THREE.BufferGeometry().setFromPoints(threePtPoints);
    const threePtLine = new THREE.Line(threePtGeo, linesMaterial);
    scene3D.add(threePtLine);

    // 5. 篮架和篮网 (篮圈高3.05m, 篮圈半径0.23m)
    const poleGeo = new THREE.CylinderGeometry(0.06, 0.06, 3.05);
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x4b5563 });
    const pole = new THREE.Mesh(poleGeo, poleMat);
    pole.position.set(0, 3.05 / 2, 0.4);
    scene3D.add(pole);

    const armGeo = new THREE.BoxGeometry(0.06, 0.06, 0.8);
    const arm = new THREE.Mesh(armGeo, poleMat);
    arm.position.set(0, 3.05, 0.8);
    scene3D.add(arm);

    const bbGeo = new THREE.BoxGeometry(1.83, 1.05, 0.04);
    const bbMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.7 });
    const bb = new THREE.Mesh(bbGeo, bbMat);
    bb.position.set(0, 2.90 + 1.05 / 2, 1.20);
    scene3D.add(bb);

    const ringGeo = new THREE.TorusGeometry(0.23, 0.015, 8, 24);
    const ringMat = new THREE.MeshStandardMaterial({ color: 0xf97316 });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.position.set(0, 3.05, 1.40);
    scene3D.add(ring);

    // 6. 运动员与轨迹
    const trajMat = new THREE.LineBasicMaterial({ color: 0xa855f7, linewidth: 3 });
    const trajGeo = new THREE.BufferGeometry();
    playerTrajectoryLine3D = new THREE.Line(trajGeo, trajMat);
    scene3D.add(playerTrajectoryLine3D);

    const ballTrajMat = new THREE.LineBasicMaterial({ color: 0xf97316, linewidth: 2 });
    const ballTrajGeo = new THREE.BufferGeometry();
    ballTrajectoryLine3D = new THREE.Line(ballTrajGeo, ballTrajMat);
    scene3D.add(ballTrajectoryLine3D);

    playerSkeleton3D = new THREE.Group();
    scene3D.add(playerSkeleton3D);

    is3DInitialized = true;

    // 自适应大小
    window.addEventListener("resize", () => {
        if (is3DInitialized && currentViewMode === "3d") {
            const w = container.clientWidth;
            const h = container.clientHeight || 260;
            camera3D.aspect = w / h;
            camera3D.updateProjectionMatrix();
            renderer3D.setSize(w, h);
        }
    });

    // 动画循环
    function animate() {
        requestAnimationFrame(animate);
        if (currentViewMode === "3d") {
            controls3D.update();
            renderer3D.render(scene3D, camera3D);
        }
    }
    animate();
}

function update3DView() {
    if (!is3DInitialized) return;

    // 1. 更新足底轨迹
    if (physicalTrajectoryPath.length > 0) {
        const points = [];
        physicalTrajectoryPath.forEach(pt => {
            points.push(new THREE.Vector3(pt.x, 0.02, pt.y));
        });
        const geo = new THREE.BufferGeometry().setFromPoints(points);
        playerTrajectoryLine3D.geometry.dispose();
        playerTrajectoryLine3D.geometry = geo;
    }

    // 2. 更新篮球三维投影轨迹
    if (ballPhysicalTrajectoryPath.length > 0) {
        const ballPoints = [];
        ballPhysicalTrajectoryPath.forEach(pt => {
            ballPoints.push(new THREE.Vector3(pt.x, pt.z || 0.08, pt.y));
        });
        const ballGeo = new THREE.BufferGeometry().setFromPoints(ballPoints);
        ballTrajectoryLine3D.geometry.dispose();
        ballTrajectoryLine3D.geometry = ballGeo;
    }

    // 3. 清除并重建 3D 关节点与骨架
    while (playerSkeleton3D.children.length > 0) {
        const obj = playerSkeleton3D.children[0];
        playerSkeleton3D.remove(obj);
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) obj.material.dispose();
    }

    if (currentSkeletonWorld3D) {
        const joints = currentSkeletonWorld3D;
        const sphereGeo = new THREE.SphereGeometry(0.06, 12, 12);
        const wristAnkleMat = new THREE.MeshStandardMaterial({ color: 0xe040fb, roughness: 0.5 });
        const normalJointMat = new THREE.MeshStandardMaterial({ color: 0x00e676, roughness: 0.5 });

        const jointPositions = {};
        for (const name in joints) {
            const pt = joints[name];
            const mesh = new THREE.Mesh(sphereGeo, name.includes("wrist") || name.includes("ankle") ? wristAnkleMat : normalJointMat);
            mesh.position.set(pt[0], pt[2], pt[1]);
            playerSkeleton3D.add(mesh);
            jointPositions[name] = mesh.position;
        }

        const connections = [
            ["left_shoulder", "right_shoulder"],
            ["left_shoulder", "left_elbow"], ["left_elbow", "left_wrist"],
            ["right_shoulder", "right_elbow"], ["right_elbow", "right_wrist"],
            ["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"],
            ["left_hip", "right_hip"],
            ["left_hip", "left_knee"], ["left_knee", "left_ankle"],
            ["right_hip", "right_knee"], ["right_knee", "right_ankle"]
        ];

        const boneMat = new THREE.LineBasicMaterial({ color: 0x00e5ff });
        connections.forEach(([p1, p2]) => {
            if (jointPositions[p1] && jointPositions[p2]) {
                const boneGeo = new THREE.BufferGeometry().setFromPoints([jointPositions[p1], jointPositions[p2]]);
                const boneLine = new THREE.Line(boneGeo, boneMat);
                playerSkeleton3D.add(boneLine);
            }
        });
    }
}
