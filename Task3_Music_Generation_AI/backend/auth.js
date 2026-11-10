// Auralis Auth — bcrypt + JWT, JSON user store
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'auralis-dev-secret-change-in-production-2026';
const DATA_DIR = path.join(__dirname, '..', 'data');
const USERS_FILE = path.join(DATA_DIR, 'users.json');

function ensure() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(USERS_FILE)) fs.writeFileSync(USERS_FILE, JSON.stringify([], null, 2));
}
function readUsers() {
  ensure();
  return new Promise((resolve) => {
    try { resolve(JSON.parse(fs.readFileSync(USERS_FILE, 'utf8'))); } catch { resolve([]); }
  });
}
function writeUsers(users) {
  ensure();
  return new Promise((resolve, reject) => {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2), 'utf8', (e) => (e ? reject(e) : resolve(true)));
  });
}
async function readAllUsers() { return readUsers(); }

function publicUser(u) {
  if (!u) return null;
  const { passwordHash, ...rest } = u;
  return rest;
}

async function register(email, password, displayName) {
  email = String(email || '').trim().toLowerCase();
  password = String(password || '');
  displayName = String(displayName || email.split('@')[0] || 'Creator').trim().slice(0, 40);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw Object.assign(new Error('Invalid email'), { status: 400 });
  if (password.length < 6) throw Object.assign(new Error('Password must be at least 6 characters'), { status: 400 });
  if (!displayName) throw Object.assign(new Error('Name required'), { status: 400 });

  const users = await readUsers();
  const existing = users.find(u => u.email === email);
  if (existing) {
    if (!existing.passwordHash) throw Object.assign(new Error('Email already registered via Google — use Google login or ask admin to link'), { status: 409 });
    throw Object.assign(new Error('Email already registered'), { status: 409 });
  }
  if (users.some(u => u.displayName.toLowerCase() === displayName.toLowerCase())) throw Object.assign(new Error('Name already taken'), { status: 409 });

  const passwordHash = await bcrypt.hash(password, 10);
  const user = {
    id: 'usr_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    email, displayName,
    passwordHash,
    createdAt: new Date().toISOString(),
    trackCount: 0,
  };
  users.push(user);
  await writeUsers(users);
  return { user: publicUser(user), token: signToken(user) };
}

async function login(email, password) {
  email = String(email || '').trim().toLowerCase();
  password = String(password || '');
  const users = await readUsers();
  const user = users.find(u => u.email === email);
  if (!user) throw Object.assign(new Error('Invalid email or password'), { status: 401 });
  if (!user.passwordHash) throw Object.assign(new Error('This account uses Google login — use Continue with Google'), { status: 401 });
  const ok = await bcrypt.compare(password, user.passwordHash);
  if (!ok) throw Object.assign(new Error('Invalid email or password'), { status: 401 });
  return { user: publicUser(user), token: signToken(user) };
}

function signToken(user) {
  return jwt.sign({ sub: user.id, email: user.email, name: user.displayName }, JWT_SECRET, { expiresIn: '7d' });
}

function verifyToken(token) {
  if (!token) return Promise.resolve(null);
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    return Promise.resolve(payload); // async verification for refresh
  } catch { return Promise.resolve(null); }
}

async function loadUserById(id) {
  const users = await readUsers();
  const u = users.find(x => x.id === id);
  return u ? publicUser(u) : null;
}

async function authenticate(token) {
  if (!token) return null;
  const payload = await verifyToken(token);
  if (!payload) return null;
  const u = await loadUserById(payload.sub);
  return u;
}

async function optionalAuth(req, res, next) {
  try {
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : (req.query?.token || null);
    req.user = await authenticate(token);
    next();
  } catch (e) { next(e); }
}
async function requireAuth(req, res, next) {
  try {
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : (req.query?.token || null);
    const u = await authenticate(token);
    if (!u) return res.status(401).json({ error: 'Login required', code: 'AUTH_REQUIRED' });
    req.user = u;
    next();
  } catch (e) { next(e); }
}

module.exports = { register, login, verifyToken, signToken, publicUser, readUsers, writeUsers, optionalAuth, requireAuth, JWT_SECRET };
