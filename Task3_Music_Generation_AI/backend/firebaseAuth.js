// Auralis Firebase Auth — verifies Firebase ID tokens (Google sign-in) via firebase-admin
// and issues our own JWT session token (same shape as email login).
const admin = require('firebase-admin');
const fs = require('fs');

function getPrivateKey() {
  const raw = String(process.env.FIREBASE_PRIVATE_KEY || '').trim();
  if (!raw) return null;
  if (raw.includes('-----BEGIN PRIVATE KEY-----')) return raw.replace(/\\n/g, '\n');
  const p = raw.replace(/^["']|["']$/g, '');
  try {
    if (p && fs.existsSync(p)) {
      const j = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (j && j.private_key) return String(j.private_key).replace(/\\n/g, '\n');
    }
  } catch (e) { /* ignore */ }
  return null;
}

function initAdmin() {
  try {
    const projectId = process.env.FIREBASE_PROJECT_ID || 'auralis-ai-93b95';
    const clientEmail = process.env.FIREBASE_CLIENT_EMAIL || 'firebase-adminsdk-fbsvc@auralis-ai-93b95.iam.gserviceaccount.com';
    const privateKey = getPrivateKey();
    if (!privateKey) { console.error('[firebaseAuth] missing private key'); return false; }
    if (!admin.apps.length) {
      admin.initializeApp({
        credential: admin.credential.cert({ projectId, clientEmail, privateKey }),
        projectId,
      });
    }
    return true;
  } catch (e) {
    console.error('[firebaseAuth] init failed:', e.message);
    return false;
  }
}

function getFirebaseConfig() {
  const enabled = initAdmin();
  return {
    enabled,
    projectId: process.env.FIREBASE_PROJECT_ID || 'auralis-ai-93b95',
    apiKey: process.env.FIREBASE_WEB_API_KEY || 'AIzaSyAiTSBpOCsToeQ342LekWI9SCqcV9cexQg',
    authDomain: process.env.FIREBASE_AUTH_DOMAIN || 'auralis-ai-93b95.firebaseapp.com',
    clientEmail: process.env.FIREBASE_CLIENT_EMAIL || 'firebase-adminsdk-fbsvc@auralis-ai-93b95.iam.gserviceaccount.com',
    hint: enabled
      ? 'Firebase admin verified — Google sign-in ready.'
      : 'Set FIREBASE_PRIVATE_KEY (or point it at the service-account JSON), FIREBASE_CLIENT_EMAIL, FIREBASE_WEB_API_KEY, FIREBASE_AUTH_DOMAIN in server env.',
  };
}

async function verifyFirebaseIdToken(idToken) {
  if (!initAdmin()) throw Object.assign(new Error('Firebase admin not configured on server (check FIREBASE_* env vars)'), { status: 503 });
  const decoded = await admin.auth().verifyIdToken(idToken);
  if (!decoded) throw Object.assign(new Error('Invalid Firebase token'), { status: 401 });
  return decoded;
}

async function loginWithFirebase(idToken) {
  const decoded = await verifyFirebaseIdToken(idToken);
  const email = String(decoded.email || '').trim().toLowerCase();
  if (!email) throw Object.assign(new Error('Firebase user has no email'), { status: 400 });
  const displayName = String(decoded.name || email.split('@')[0] || 'Creator').trim().slice(0, 40);

  const authMod = require('./auth');
  const users = await authMod.readUsers();
  let user = users.find(u => u.email === email);
  if (user) {
    if (!user.passwordHash && user.provider !== 'firebase') {
      user.provider = 'local+firebase';
      user.firebaseUid = decoded.uid;
      await authMod.writeUsers(users);
    }
  } else {
    user = {
      id: 'usr_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      email, displayName,
      passwordHash: null,
      provider: 'firebase',
      firebaseUid: decoded.uid,
      createdAt: new Date().toISOString(),
      trackCount: 0,
    };
    users.push(user);
    await authMod.writeUsers(users);
  }
  const token = authMod.signToken(user);
  return { user: authMod.publicUser(user), token, provider: 'firebase', firebaseUid: decoded.uid || null };
}

module.exports = { loginWithFirebase, verifyFirebaseIdToken, getFirebaseConfig, initAdmin };
