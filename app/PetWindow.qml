import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import "Physics.js" as Physics

PanelWindow {
    id: root
    required property ShellScreen modelData
    required property var snapshot
    readonly property var monitor: snapshot.monitors.find(m => m.name === modelData.name)
    readonly property var config: snapshot.config
    property var platforms: []
    property var arrivals: ({})
    readonly property bool foreground: sprite.needsForeground

    screen: modelData
    color: "transparent"
    visible: snapshot.connected && !!monitor && !(config.excludedScreens ?? []).includes(modelData.name)
    anchors { top: true; bottom: true; left: true; right: true }
    WlrLayershell.namespace: "miku-desktop"
    WlrLayershell.layer: foreground ? WlrLayer.Overlay : WlrLayer.Bottom
    WlrLayershell.exclusionMode: ExclusionMode.Ignore
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    mask: sprite.inputRegion

    function refresh() {
        const overlays = snapshot.notifications[modelData.name] ?? [];
        platforms = Physics.windowPlatforms(snapshot.clients, monitor, width, height, overlays);
        const now = Date.now();
        const next = {};
        for (const popup of overlays) next[popup.id] = arrivals[popup.id] ?? {since: now, jumped: false};
        arrivals = next;
        if (!config.autoNotificationHop || sprite.dragging || !sprite.body.grounded) return;
        const pending = Object.keys(next).filter(id => !next[id].jumped
            && now - next[id].since >= (config.notificationDelayMs ?? 600))
            .sort((a,b) => next[b].since - next[a].since);
        for (const id of pending) {
            const perch = platforms.find(p => p.id.startsWith(id + ":"));
            if (perch && sprite.hopToPlatform(perch)) { next[id].jumped = true; break; }
        }
    }
    Timer { interval: 100; repeat: true; running: root.visible; triggeredOnStart: true; onTriggered: root.refresh() }

    PetSprite {
        id: sprite
        screenSize: Qt.size(root.width,root.height)
        borderThickness: 0
        floorOffset: root.monitor?.reserved?.[3] ?? 0
        imgPath: root.config.spritePath ?? ""
        platforms: root.platforms
    }

    IpcHandler {
        target: "pet-" + root.modelData.name
        function status(): string {
            return JSON.stringify({screen: root.modelData.name, visible: root.visible,
                layer: root.foreground ? "overlay" : "desktop", body: sprite.body,
                platforms: root.platforms, arrivals: root.arrivals,
                notificationAdapter: root.snapshot.adapters?.[root.modelData.name] ?? "none"});
        }
        function perch(): void { sprite.hopToPerch(); }
        function drop(x: real, y: real): void { sprite.dropAt(x,y); }
        function home(): void {
            sprite.body = Physics.initial(Math.min(sprite.x,root.width-128),sprite.floor);
        }
    }
}
