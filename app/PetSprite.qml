import QtQuick
import Quickshell
import "Physics.js" as Physics

Item {
    id: root
    required property var screenSize
    required property var borderThickness
    required property string imgPath
    property real floorOffset: 0
    property var platforms: []
    readonly property real floor: screenSize.height - borderThickness - floorOffset
    readonly property var bounds: ({width: screenSize.width, floor: floor})
    property var body: Physics.initial(50, floor)
    property bool dragging: false
    readonly property bool needsForeground: dragging || !body.grounded || body.support !== "floor"
    property point dragOffset
    property real dragVx: 0
    property real dragVy: 0
    property real lastDragTime: 0
    property string currentAnim: "idle"
    property int frameIndex: 0

    // The rest of the overlay passes input through to notifications and apps.
    readonly property Region inputRegion: Region {
        x: root.x + 16
        y: root.y + 4
        width: 96
        height: 124
    }

    width: 128
    height: 128
    x: body.x
    y: body.y

    function pickIdle() {
        const choices = body.support.startsWith("window:") || body.support.startsWith("notification:")
            ? ["sit", "sit", "lookUp", "sleep"] : ["idle", "lookUp", "dangle", "sleep"];
        currentAnim = choices[Math.floor(Math.random() * choices.length)];
        frameIndex = 0;
    }

    function dropAt(px, py) {
        body = Object.assign({}, body, {
            x: Physics.clamp(px, 0, screenSize.width - width),
            y: Physics.clamp(py, 0, floor - height),
            vx: 0, vy: 0, grounded: false, support: "", target: null
        });
    }

    function hopToPlatform(platform) {
        if (dragging || !platform) return false;
        body = Physics.jumpTo(body, platform, screenSize.width);
        currentAnim = "idle";
        return true;
    }

    function hopToPerch() {
        const options = platforms.filter(p => p.id !== body.support && p.top <= floor);
        if (!options.length) return false;
        return hopToPlatform(options[Math.floor(Math.random() * options.length)]);
    }

    function walkRandom() {
        const support = platforms.find(p => p.id === body.support);
        const left = Math.max(0, (support?.left ?? 0) + 20 - width / 2);
        const right = Math.min(screenSize.width - width, (support?.right ?? screenSize.width) - 20 - width / 2);
        if (right <= left) return;
        body = Object.assign({}, body, {target: left + Math.random() * (right - left)});
        currentAnim = "walk";
        frameIndex = 0;
    }

    function animFrame(anim, index) {
        const frames = {
            idle: [1], lookUp: [26], sit: [11],
            dangle: [31, 32, 31, 33], sleep: [20, 21],
            walk: [1, 2, 1, 3], eat: [26, 15, 27, 16, 28, 17, 29, 11]
        };
        const list = frames[anim] ?? frames.idle;
        return "shime" + list[index % list.length] + ".png";
    }

    Component.onCompleted: {
        body = Physics.initial(Math.random() * Math.max(0, screenSize.width - width), floor);
        pickIdle();
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: root.dragging ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property real pressX: 0
        property real pressY: 0
        property bool moved: false
        property string pressedAnim: "idle"

        onPressed: mouse => {
            if (mouse.button === Qt.RightButton) return;
            root.dragging = true;
            root.dragOffset = Qt.point(mouse.x, mouse.y);
            pressX = root.x; pressY = root.y; moved = false;
            root.lastDragTime = Date.now();
            root.dragVx = 0; root.dragVy = 0;
            pressedAnim = root.currentAnim;
            root.currentAnim = "idle";
            root.body = Object.assign({}, root.body, {vx: 0, vy: 0, target: null});
        }
        onPositionChanged: mouse => {
            if (!root.dragging) return;
            const px = Physics.clamp(root.x + mouse.x - root.dragOffset.x, 0, root.screenSize.width - root.width);
            const py = Physics.clamp(root.y + mouse.y - root.dragOffset.y, 0, root.floor - root.height);
            const now = Date.now();
            const dt = Math.max(0.008, (now - root.lastDragTime) / 1000);
            root.dragVx = Physics.clamp((px - root.x) / dt, -1600, 1600);
            root.dragVy = Physics.clamp((py - root.y) / dt, -1600, 1600);
            root.lastDragTime = now;
            moved = moved || Math.abs(px - pressX) + Math.abs(py - pressY) > 4;
            root.body = Object.assign({}, root.body, {x: px, y: py});
        }
        onReleased: mouse => {
            if (mouse.button === Qt.RightButton) { root.hopToPerch(); return; }
            root.dragging = false;
            if (!moved) {
                root.currentAnim = pressedAnim === "eat" ? "sleep" : "eat";
                root.frameIndex = 0;
                return;
            }
            const stale = Date.now() - root.lastDragTime > 100;
            root.body = Object.assign({}, root.body, {
                vx: stale ? 0 : root.dragVx, vy: stale ? 0 : root.dragVy,
                grounded: false, support: "", target: null
            });
        }
        onCanceled: {
            root.dragging = false;
            root.dropAt(root.x, root.y);
        }
    }

    Image {
        anchors.fill: parent
        source: "file://" + root.imgPath + root.animFrame(root.currentAnim, root.frameIndex)
        sourceSize: Qt.size(128, 128)
        fillMode: Image.PreserveAspectFit
        mirror: root.body.facingRight
    }

    FrameAnimation {
        running: root.visible && !root.dragging
        onTriggered: {
            const wasGrounded = root.body.grounded;
            const wasWalking = root.body.target !== null;
            root.body = Physics.step(root.body, root.platforms, root.bounds, frameTime);
            if ((!wasGrounded && root.body.grounded) || (wasWalking && root.body.target === null && root.body.grounded))
                root.pickIdle();
        }
    }
    Timer {
        interval: 200
        repeat: true
        running: root.visible && !root.dragging
        onTriggered: root.frameIndex++
    }
    Timer {
        interval: 7000
        repeat: true
        running: root.visible
        onTriggered: {
            if (root.dragging || !root.body.grounded || root.body.target !== null) return;
            const roll = Math.random();
            // Keep spontaneous activity on the desktop; hopping is user initiated.
            if (roll < 0.5) root.walkRandom();
            else root.pickIdle();
        }
    }
}
