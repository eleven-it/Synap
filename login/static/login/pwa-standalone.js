/**
 * Detección PWA standalone (Android display-mode / iOS navigator.standalone).
 */
(function (global) {
  function isPwaStandalone() {
    if (typeof window === 'undefined') return false;
    if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
      return true;
    }
    if (window.navigator && window.navigator.standalone === true) {
      return true;
    }
    return false;
  }

  global.SynapPwa = global.SynapPwa || {};
  global.SynapPwa.isPwaStandalone = isPwaStandalone;
})(typeof window !== 'undefined' ? window : this);
