/**
 * Cliente WebAuthn Synap: registro, unlock y revocación (CSRF + base64url).
 */
(function (global) {
  'use strict';

  var API_BASE = '/login/api/webauthn';

  function getCookie(name) {
    var v = '; ' + document.cookie;
    var parts = v.split('; ' + name + '=');
    return parts.length === 2 ? parts.pop().split(';').shift() : '';
  }

  function csrfHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    };
  }

  function bufferDecode(value) {
    var padding = '='.repeat((4 - (value.length % 4)) % 4);
    var base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/');
    var raw = window.atob(base64);
    var out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i += 1) {
      out[i] = raw.charCodeAt(i);
    }
    return out.buffer;
  }

  function bufferEncode(buffer) {
    var bytes = new Uint8Array(buffer);
    var str = '';
    for (var i = 0; i < bytes.byteLength; i += 1) {
      str += String.fromCharCode(bytes[i]);
    }
    return window.btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  function parseCreationOptions(options) {
    options.challenge = bufferDecode(options.challenge);
    options.user.id = bufferDecode(options.user.id);
    if (options.excludeCredentials) {
      options.excludeCredentials = options.excludeCredentials.map(function (c) {
        return {
          type: c.type,
          id: bufferDecode(c.id),
          transports: c.transports,
        };
      });
    }
    return options;
  }

  function parseRequestOptions(options) {
    options.challenge = bufferDecode(options.challenge);
    if (options.allowCredentials) {
      options.allowCredentials = options.allowCredentials.map(function (c) {
        return {
          type: c.type,
          id: bufferDecode(c.id),
          transports: c.transports,
        };
      });
    }
    return options;
  }

  function credentialToJSON(credential) {
    var response = credential.response;
    var clientExtensionResults = {};
    if (credential.getClientExtensionResults) {
      clientExtensionResults = credential.getClientExtensionResults();
    }
    var attestationObject;
    var authenticatorData;
    var signature;
    var userHandle = null;
    if (response.attestationObject) {
      attestationObject = bufferEncode(response.attestationObject);
    }
    if (response.authenticatorData) {
      authenticatorData = bufferEncode(response.authenticatorData);
    }
    if (response.signature) {
      signature = bufferEncode(response.signature);
    }
    if (response.userHandle) {
      userHandle = bufferEncode(response.userHandle);
    }
    return {
      id: credential.id,
      rawId: bufferEncode(credential.rawId),
      type: credential.type,
      authenticatorAttachment: credential.authenticatorAttachment || undefined,
      clientExtensionResults: clientExtensionResults,
      response: {
        attestationObject: attestationObject,
        authenticatorData: authenticatorData,
        signature: signature,
        userHandle: userHandle,
        clientDataJSON: bufferEncode(response.clientDataJSON),
      },
    };
  }

  function apiPost(path, body) {
    return fetch(API_BASE + path, {
      method: 'POST',
      headers: csrfHeaders(),
      credentials: 'same-origin',
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) {
          var err = new Error(data.error || 'Error WebAuthn');
          err.status = r.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  function apiGet(path) {
    return fetch(API_BASE + path, {
      method: 'GET',
      credentials: 'same-origin',
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) {
          var err = new Error(data.error || 'Error WebAuthn');
          err.status = r.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  function getPreference() {
    return apiGet('/preference/');
  }

  function setPreference(enabled) {
    return apiPost('/preference/', { enabled: !!enabled });
  }

  function registerPasskey(deviceLabel) {
    if (!window.PublicKeyCredential) {
      return Promise.reject(new Error('WebAuthn no disponible en este navegador'));
    }
    return apiPost('/register/options/', { device_label: deviceLabel || '' })
      .then(function (options) {
        return navigator.credentials.create({
          publicKey: parseCreationOptions(options),
        });
      })
      .then(function (credential) {
        return apiPost('/register/verify/', { credential: credentialToJSON(credential) });
      });
  }

  function authenticatePasskey(baseEmpresa, codUsuario) {
    if (!window.PublicKeyCredential) {
      return Promise.reject(new Error('WebAuthn no disponible en este navegador'));
    }
    return apiPost('/authenticate/options/', {
      base_empresa: baseEmpresa,
      cod_usuario: codUsuario,
    })
      .then(function (options) {
        return navigator.credentials.get({
          publicKey: parseRequestOptions(options),
        });
      })
      .then(function (credential) {
        return apiPost('/authenticate/verify/', { credential: credentialToJSON(credential) });
      });
  }

  function listCredentials() {
    return apiGet('/credentials/');
  }

  function revokeCredential(credentialId) {
    return apiPost('/credentials/revoke/', { credential_id: credentialId });
  }

  function revokeAllCredentials() {
    return apiPost('/credentials/revoke/', { all: true });
  }

  global.SynapWebAuthn = {
    registerPasskey: registerPasskey,
    authenticatePasskey: authenticatePasskey,
    listCredentials: listCredentials,
    revokeCredential: revokeCredential,
    revokeAllCredentials: revokeAllCredentials,
    getPreference: getPreference,
    setPreference: setPreference,
    isSupported: function () {
      return !!window.PublicKeyCredential;
    },
  };
})(typeof window !== 'undefined' ? window : this);
