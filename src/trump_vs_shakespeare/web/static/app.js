"use strict";

const $ = (id) => document.getElementById(id);
const ui = {
  lobby: $("lobby"), arena: $("arena"), localBtn: $("localBtn"), onlineBtn: $("onlineBtn"),
  joinForm: $("joinForm"), roomInput: $("roomInput"), lobbyError: $("lobbyError"), gameError: $("gameError"),
  roomCode: $("roomCode"), matchTitle: $("matchTitle"), connection: $("connection"), shareBtn: $("shareBtn"), leaveBtn: $("leaveBtn"), restartBtn: $("restartBtn"),
  trumpHealth: $("trumpHealth"), trumpHealthText: $("trumpHealthText"), trumpEnergy: $("trumpEnergy"), trumpGuard: $("trumpGuard"), trumpMoves: $("trumpMoves"), trumpPending: $("trumpPending"),
  shakespeareHealth: $("shakespeareHealth"), shakespeareHealthText: $("shakespeareHealthText"), shakespeareEnergy: $("shakespeareEnergy"), shakespeareGuard: $("shakespeareGuard"), shakespeareMoves: $("shakespeareMoves"), shakespearePending: $("shakespearePending"),
  roundLabel: $("roundLabel"), battleLog: $("battleLog")
};

const session = {
  room: null, token: null, mode: null, controlledSides: [], rematchVotes: [],
  state: null, socket: null, reconnects: 0, pingTimer: null
};

ui.localBtn.addEventListener("click", () => createRoom("local"));
ui.onlineBtn.addEventListener("click", () => createRoom("online"));
ui.joinForm.addEventListener("submit", (event) => { event.preventDefault(); joinRoom(ui.roomInput.value); });
ui.shareBtn.addEventListener("click", shareRoom);
ui.roomCode.addEventListener("click", shareRoom);
ui.leaveBtn.addEventListener("click", leaveRoom);
ui.restartBtn.addEventListener("click", () => send({ type: "restart" }));
ui.roomInput.addEventListener("input", () => { ui.roomInput.value = ui.roomInput.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 6); });

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "The server rejected the request.");
  return data;
}

async function createRoom(mode) {
  clearError("lobby");
  setBusy(true);
  try {
    const data = await request("/api/rooms", { method: "POST", body: JSON.stringify({ mode }) });
    enterRoom(data);
  } catch (error) { showError("lobby", error.message); }
  finally { setBusy(false); }
}

async function joinRoom(rawCode) {
  const code = rawCode.trim().toUpperCase();
  clearError("lobby");
  if (code.length !== 6) return showError("lobby", "Enter the six-character room code.");
  setBusy(true);
  try {
    const data = await request("/api/rooms/join", { method: "POST", body: JSON.stringify({ code }) });
    enterRoom(data);
  } catch (error) { showError("lobby", error.message); }
  finally { setBusy(false); }
}

function enterRoom(data) {
  session.room = data.room_code;
  session.token = data.token;
  session.mode = data.mode;
  session.controlledSides = data.controlled_sides;
  session.rematchVotes = data.rematch_votes || [];
  session.state = data.state;
  sessionStorage.setItem("tvs-session", JSON.stringify({ room: session.room, token: session.token }));
  history.replaceState({}, "", `/?room=${encodeURIComponent(session.room)}`);
  ui.lobby.hidden = true;
  ui.arena.hidden = false;
  ui.roomCode.textContent = session.room;
  render();
  connectSocket();
}

function connectSocket() {
  if (!session.room || !session.token) return;
  if (session.socket) session.socket.close();
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(
    `${protocol}//${location.host}/ws/${encodeURIComponent(session.room)}`,
    `tvs-token.${session.token}`
  );
  session.socket = socket;
  ui.connection.textContent = "Connecting…";
  ui.connection.classList.remove("online");
  socket.addEventListener("open", () => {
    session.reconnects = 0;
    ui.connection.textContent = "Live";
    ui.connection.classList.add("online");
    clearInterval(session.pingTimer);
    session.pingTimer = setInterval(() => send({ type: "ping" }), 25000);
  });
  socket.addEventListener("message", ({ data }) => {
    let message;
    try { message = JSON.parse(data); }
    catch { return showError("game", "The server sent an invalid message."); }
    if (message.type === "hello") {
      session.mode = message.mode;
      session.controlledSides = message.controlled_sides;
      session.rematchVotes = message.rematch_votes || [];
      session.state = message.state;
      render();
    } else if (message.type === "state") {
      session.rematchVotes = message.rematch_votes || [];
      session.state = message.state;
      render();
    } else if (message.type === "error") {
      showError("game", message.message);
    }
  });
  socket.addEventListener("close", () => {
    clearInterval(session.pingTimer);
    ui.connection.textContent = "Reconnecting…";
    ui.connection.classList.remove("online");
    if (!session.room) return;
    const delay = Math.min(10000, 600 * (2 ** session.reconnects++));
    setTimeout(connectSocket, delay);
  });
  socket.addEventListener("error", () => socket.close());
}

function send(message) {
  clearError("game");
  if (!session.socket || session.socket.readyState !== WebSocket.OPEN) return showError("game", "Connection is not ready yet.");
  session.socket.send(JSON.stringify(message));
}

function chooseMove(side, moveId) {
  const message = { type: "action", move_id: moveId };
  if (session.mode === "local") message.actor = side;
  send(message);
}

function render() {
  const state = session.state;
  if (!state) return;
  ui.roundLabel.textContent = `ROUND ${state.round}`;
  const waiting = state.status === "waiting";
  if (waiting) ui.matchTitle.textContent = "Waiting for Shakespeare to join…";
  else if (state.status === "finished") ui.matchTitle.textContent = state.winner === "draw" ? "The duel ends in a draw" : `${displayName(state.winner)} wins the duel`;
  else if (session.mode === "local") ui.matchTitle.textContent = "Local duel — choose both actions";
  else ui.matchTitle.textContent = `You command ${displayName(session.controlledSides[0])}`;

  ui.restartBtn.hidden = state.status !== "finished";
  const voted = session.controlledSides.some((side) => session.rematchVotes.includes(side));
  ui.restartBtn.disabled = session.mode === "online" && voted;
  ui.restartBtn.textContent = session.mode === "online" && voted ? "Waiting for opponent…" : (session.mode === "online" ? "Request rematch" : "Play again");
  ui.shareBtn.hidden = session.mode === "local";

  renderFighter("trump", state.fighters.trump, state.moves.trump, state.pending.trump);
  renderFighter("shakespeare", state.fighters.shakespeare, state.moves.shakespeare, state.pending.shakespeare);
  renderLog(state.log);
}

function renderFighter(side, fighter, moves, pending) {
  ui[`${side}Health`].style.width = `${Math.max(0, fighter.health)}%`;
  ui[`${side}HealthText`].textContent = `${fighter.health} / 100`;
  ui[`${side}Energy`].textContent = fighter.energy;
  ui[`${side}Guard`].textContent = fighter.guard;
  ui[`${side}Pending`].hidden = !pending;
  const container = ui[`${side}Moves`];
  container.replaceChildren();
  const controlled = session.controlledSides.includes(side);
  for (const move of moves) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "move";
    button.disabled = !controlled || pending || session.state.status !== "playing" || move.cost > fighter.energy;
    const title = document.createElement("strong");
    const name = document.createElement("span"); name.textContent = move.name;
    const cost = document.createElement("span"); cost.textContent = `${move.cost} EN`;
    title.append(name, cost);
    const description = document.createElement("small"); description.textContent = move.description;
    const stats = document.createElement("div"); stats.className = "move-stats";
    const values = [["DMG", move.damage], ["ACC", `${move.accuracy}%`], ["SPD", move.priority]];
    if (move.guard) values.push(["GRD", move.guard]);
    if (move.heal) values.push(["HEAL", move.heal]);
    for (const [label, value] of values) { const tag = document.createElement("span"); tag.textContent = `${label} ${value}`; stats.append(tag); }
    button.append(title, description, stats);
    button.addEventListener("click", () => chooseMove(side, move.id));
    container.append(button);
  }
}

function renderLog(log) {
  ui.battleLog.replaceChildren();
  for (const entry of log.slice().reverse()) {
    if (entry.private) continue;
    const item = document.createElement("li");
    item.className = entry.actor === "system" ? "system" : entry.actor;
    item.textContent = entry.message;
    ui.battleLog.append(item);
  }
}

async function shareRoom() {
  const url = `${location.origin}/?room=${encodeURIComponent(session.room)}`;
  const shareData = { title: "Trump vs. Shakespeare", text: `Join room ${session.room}`, url };
  try {
    if (navigator.share) await navigator.share(shareData);
    else { await navigator.clipboard.writeText(url); ui.matchTitle.textContent = "Invite link copied"; }
  } catch (error) { if (error.name !== "AbortError") showError("game", "Could not share the room link."); }
}

function leaveRoom() {
  session.room = null;
  session.token = null;
  session.rematchVotes = [];
  sessionStorage.removeItem("tvs-session");
  if (session.socket) session.socket.close();
  history.replaceState({}, "", "/");
  ui.arena.hidden = true;
  ui.lobby.hidden = false;
}

function showError(place, message) {
  const target = place === "lobby" ? ui.lobbyError : ui.gameError;
  target.textContent = message;
  target.hidden = false;
  if (place === "game") setTimeout(() => { target.hidden = true; }, 5000);
}
function clearError(place) { (place === "lobby" ? ui.lobbyError : ui.gameError).hidden = true; }
function setBusy(busy) { ui.localBtn.disabled = busy; ui.onlineBtn.disabled = busy; }
function displayName(side) { return side === "trump" ? "Trump" : side === "shakespeare" ? "Shakespeare" : "Nobody"; }

async function restoreOrPrefill() {
  const roomFromUrl = new URLSearchParams(location.search).get("room");
  if (roomFromUrl) ui.roomInput.value = roomFromUrl.toUpperCase().slice(0, 6);
  const stored = JSON.parse(sessionStorage.getItem("tvs-session") || "null");
  if (!stored || stored.room !== roomFromUrl) return;
  try {
    const data = await request(`/api/rooms/${encodeURIComponent(stored.room)}`, {
      headers: { Authorization: `Bearer ${stored.token}` }
    });
    enterRoom({ room_code: stored.room, token: stored.token, ...data });
  } catch { sessionStorage.removeItem("tvs-session"); }
}

if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
restoreOrPrefill();
