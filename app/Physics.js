// Logical screen coordinates; velocities are pixels per second.
var SIZE = 128;
var GRAVITY = 1800;

function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }

function windowPlatforms(clients, monitor, width, height, overlays) {
    if (!monitor) return [];
    var special = monitor.specialWorkspace && monitor.specialWorkspace.id;
    var active = special || (monitor.activeWorkspace && monitor.activeWorkspace.id);
    var rects = clients.filter(function(c) {
        return c.mapped && !c.hidden && c.visible !== false && c.monitor === monitor.id
            && (c.pinned || (c.workspace && c.workspace.id === active))
            && c.at && c.size;
    }).map(function(c) {
        return {id: "window:" + c.address, left: c.at[0] - monitor.x,
            right: c.at[0] - monitor.x + c.size[0], top: c.at[1] - monitor.y,
            bottom: c.at[1] - monitor.y + c.size[1],
            rank: (c.floating ? 100000 : 0) - (c.focusHistoryID < 0 ? 99999 : c.focusHistoryID),
            landable: !c.fullscreen};
    });
    rects = rects.concat(overlays || []).sort(function(a,b) { return b.rank - a.rank; });
    var result = [];
    rects.forEach(function(r, index) {
        if (r.landable === false || r.top < SIZE || r.top > height) return;
        var segments = [[Math.max(0, r.left), Math.min(width, r.right)]];
        // Remove portions of an edge hidden behind a foreground window/popup.
        rects.slice(0, index).forEach(function(o) {
            if (o.top > r.top || o.bottom <= r.top) return;
            var next = [];
            segments.forEach(function(s) {
                if (o.right <= s[0] || o.left >= s[1]) next.push(s);
                else {
                    if (o.left > s[0]) next.push([s[0], o.left]);
                    if (o.right < s[1]) next.push([o.right, s[1]]);
                }
            });
            segments = next;
        });
        segments.forEach(function(s, i) {
            if (s[1] - s[0] >= 40)
                result.push({id: r.id + ":" + i, left: s[0], right: s[1], top: r.top});
        });
    });
    return result;
}

function initial(x, floor) {
    return {x: x, y: floor - SIZE, vx: 0, vy: 0, grounded: true,
        support: "floor", supportLeft: 0, target: null, facingRight: true};
}

function supports(p, x) { return x + SIZE / 2 >= p.left + 12 && x + SIZE / 2 <= p.right - 12; }

function step(body, platforms, bounds, dt) {
    var s = Object.assign({}, body);
    dt = clamp(dt, 0, 0.05); // Avoid giant jumps after suspend or a stalled frame.
    var floor = {id: "floor", left: 0, right: bounds.width, top: bounds.floor};
    var all = platforms.concat([floor]);
    if (s.grounded) {
        var support = all.find(function(p) { return p.id === s.support; });
        if (support) {
            var shift = support.left - s.supportLeft;
            s.x += shift;
            if (s.target !== null) s.target += shift;
            if (supports(support, s.x)) {
                s.y = support.top - SIZE;
                s.supportLeft = support.left;
            } else support = null;
        }
        if (!support) { s.grounded = false; s.support = ""; s.target = null; }
    }
    if (s.grounded && s.target !== null) {
        var dx = s.target - s.x;
        s.vx = Math.sign(dx) * Math.min(65, Math.abs(dx) / Math.max(dt, 0.001));
        s.facingRight = dx > 0;
        if (Math.abs(dx) < 1) { s.target = null; s.vx = 0; }
    } else if (s.grounded) s.vx = 0;
    if (!s.grounded) s.vy += GRAVITY * dt;
    var oldX = s.x, oldBottom = s.y + SIZE;
    s.x += s.vx * dt;
    s.y += s.vy * dt;
    if (s.x < 0) { s.x = 0; s.vx = Math.abs(s.vx) * 0.8; }
    if (s.x > bounds.width - SIZE) { s.x = bounds.width - SIZE; s.vx = -Math.abs(s.vx) * 0.8; }
    if (s.y < 0) { s.y = 0; s.vy = Math.abs(s.vy) * 0.5; }
    if (s.grounded && s.support !== "floor") {
        var edge = all.find(function(p) { return p.id === s.support; });
        if (!edge || !supports(edge, s.x)) { s.grounded = false; s.support = ""; s.target = null; }
    }
    if (!s.grounded && s.vy >= 0) {
        var bottom = s.y + SIZE;
        var hits = all.filter(function(p) {
            if (oldBottom > p.top + 1 || bottom < p.top) return false;
            var fraction = clamp((p.top - oldBottom) / Math.max(0.001, bottom - oldBottom), 0, 1);
            return supports(p, oldX + (s.x - oldX) * fraction);
        }).sort(function(a,b) { return a.top - b.top; });
        var hit = hits[0];
        if (hit) {
            s.y = hit.top - SIZE;
            s.target = null;
            if (hit.id === "floor" && s.vy > 180) {
                s.vy = -s.vy * 0.5;
                s.vx *= 0.75;
            } else {
                // Land squarely even after a fast diagonal throw.
                s.x = clamp(s.x, Math.max(0, hit.left + 12 - SIZE / 2),
                    Math.min(bounds.width - SIZE, hit.right - 12 - SIZE / 2));
                s.vy = 0; s.vx = 0; s.grounded = true;
                s.support = hit.id; s.supportLeft = hit.left;
            }
        }
    }
    if (s.y > bounds.floor - SIZE) {
        s.y = bounds.floor - SIZE; s.vy = 0; s.vx = 0;
        s.grounded = true; s.support = "floor"; s.supportLeft = 0;
    }
    return s;
}

function jumpTo(body, platform, width) {
    var s = Object.assign({}, body);
    var targetX = clamp((platform.left + platform.right - SIZE) / 2, 0, width - SIZE);
    var rise = s.y + SIZE - platform.top;
    var speed = Math.sqrt(2 * GRAVITY * (Math.max(0, rise) + 45));
    var time = (speed + Math.sqrt(Math.max(0, speed * speed - 2 * GRAVITY * rise))) / GRAVITY;
    s.vx = (targetX - s.x) / time; s.vy = -speed;
    s.grounded = false; s.support = ""; s.target = null;
    s.facingRight = s.vx > 0;
    return s;
}
