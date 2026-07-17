/**
 * Detección PWA / app instalada (Android display-mode, iOS standalone, etc.).
 * Guarda un marcador local cuando se detecta standalone para no perder el
 * contexto en navegaciones posteriores del mismo dispositivo.
 */
(function (global) {
  var STORAGE_KEY = 'synap_pwa_standalone';

  function _matchDisplayMode(mode) {
    try {
      return !!(window.matchMedia && window.matchMedia('(display-mode: ' + mode + ')').matches);
    } catch (e) {
      return false;
    }
  }

  function _detectLiveStandalone() {
    if (typeof window === 'undefined') return false;
    if (_matchDisplayMode('standalone')) return true;
    if (_matchDisplayMode('fullscreen')) return true;
    if (_matchDisplayMode('minimal-ui')) return true;
    if (_matchDisplayMode('window-controls-overlay')) return true;
    if (window.navigator && window.navigator.standalone === true) return true;
    try {
      var ref = document.referrer || '';
      if (ref.indexOf('android-app://') === 0) return true;
    } catch (e) { /* ignore */ }
    return false;
  }

  function _rememberStandalone() {
    try {
      window.localStorage.setItem(STORAGE_KEY, '1');
    } catch (e) { /* ignore */ }
  }

  function _wasStandalone() {
    try {
      return window.localStorage.getItem(STORAGE_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function isPwaStandalone() {
    if (_detectLiveStandalone()) {
      _rememberStandalone();
      return true;
    }
    return _wasStandalone();
  }

  /**
   * Contexto donde tiene sentido enroll/unlock: PWA detectada o WebAuthn
   * usable en secure context (HTTPS / localhost).
   */
  function canUseWebAuthnSurface() {
    if (typeof window === 'undefined') return false;
    if (!window.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
      return false;
    }
    return isPwaStandalone() || !!window.PublicKeyCredential;
  }

  global.SynapPwa = global.SynapPwa || {};
  global.SynapPwa.isPwaStandalone = isPwaStandalone;
  global.SynapPwa.canUseWebAuthnSurface = canUseWebAuthnSurface;
})(typeof window !== 'undefined' ? window : this);
