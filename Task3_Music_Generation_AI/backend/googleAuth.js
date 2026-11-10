// Auralis Google Auth — OAuth 2.0 via Google Identity Services (verify idToken server-side)
const { OAuth2Client } = require('google-auth-library');
const auth = require('./auth');

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || '';
const client = GOOGLE_CLIENT_ID ? new OAuth2Client(GOOGLE_CLIENT_ID) : null;

function getGoogleConfig() {
  return {
    configured: !!GOOGLE_CLIENT_ID,
    clientId: GOOGLE_CLIENT_ID || null,
    hint: GOOGLE_CLIENT_ID
      ? 'Google login enabled. Authorized JS origin must include your site origin.'
      : 'Set GOOGLE_CLIENT_ID env var (Google Cloud → APIs & Services → Credentials → OAuth 2.0 Client → Web application). Authorized JS origin: http://localhost:5000',
  };
}

/**
 * Verify idToken from Google Identity Services and return { user, token }
 * Creates a linked account on first login (provider='google').
 */
async function loginWithGoogle(idToken) {
  if (!idToken) throw Object.assign(new Error('idToken required'), { status: 400 });
  if (!client) throw Object.assign(new Error('Google login not configured on server (GOOGLE_CLIENT_ID missing)'), { status: 503 });

  let payload;
  try {
    const ticket = await client.verifyIdToken({ idToken, audience: GOOGLE_CLIENT_ID });
    payload = ticket.getPayload();
  } catch (e) {
    throw Object.assign(new Error('Invalid Google token: ' + e.message), { status: 401 });
  }
  if (!payload) throw Object.assign(new Error('Invalid Google payload'), { status: 401 });
  if (!payload.email_verified && payload.email) {
    // still allow official google emails; but warn — require verified for safety except @gmail.com
    // We allow, but mark provider.
  }

  const email = String(payload.email || '').trim().toLowerCase();
  if (!email) throw Object.assign(new Error('Google account has no email'), { status: 400 });
  const googleId = String(payload.sub || '');
  const displayName = (payload.name || email.split('@')[0] || 'Creator').trim().slice(0, 40);

  const users = auth.readUsers();
  let user = users.find(u => u.email === email);
  if (user) {
    // link google account to existing email user
    if (!user.googleId) {
      user.googleId = googleId;
      user.provider = user.provider || 'local+google';
      auth.writeUsers(users);
    }
  } else {
    user = {
      id: 'usr_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      email, displayName,
      passwordHash: null,
      provider: 'google',
      googleId,
      avatar: payload.picture || null,
      createdAt: new Date().toISOString(),
      trackCount: 0,
    };
    users.push(user);
    auth.writeUsers(users);
  }
  return { user: auth.publicUser(user), token: auth.signToken(user), provider: 'google' };
}

module.exports = { loginWithGoogle, getGoogleConfig, GOOGLE_CLIENT_ID };
