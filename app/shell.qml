pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Io

ShellRoot {
    id: root
    settings.watchFiles: false
    property var snapshot: ({connected: false, clients: [], monitors: [], notifications: {}, config: {}})

    Process {
        id: backend
        command: [Quickshell.env("MIKU_DESKTOP_COMMAND"), "stream"]
        running: true
        stdout: SplitParser {
            onRead: data => {
                try { root.snapshot = JSON.parse(data); }
                catch (error) { console.warn("Invalid Miku backend snapshot"); }
            }
        }
        onExited: {
            root.snapshot = Object.assign({}, root.snapshot, {connected: false});
            retry.start();
        }
    }
    Timer { id: retry; interval: 2000; onTriggered: backend.running = true }

    Variants {
        model: root.snapshot.connected ? Quickshell.screens : []
        PetWindow { snapshot: root.snapshot }
    }
}
