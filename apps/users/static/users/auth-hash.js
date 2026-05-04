// Client-side password hashing.
// Hashes the password with PBKDF2-SHA256 using the (lowercased+trimmed) email
// as the salt, 100,000 iterations, 32-byte output, hex-encoded — byte-for-byte
// identical to apps/users/client_hash.py:derive_client_hash so a logon attempt
// posts a value the server can verify.
(function () {
  function toHex(buf) {
    const view = new Uint8Array(buf);
    const out = new Array(view.length);
    for (let i = 0; i < view.length; i++) {
      out[i] = view[i].toString(16).padStart(2, "0");
    }
    return out.join("");
  }

  async function deriveClientHash(password, email) {
    const enc = new TextEncoder();
    const salt = enc.encode(email.trim().toLowerCase());
    const keyMaterial = await window.crypto.subtle.importKey(
      "raw",
      enc.encode(password),
      { name: "PBKDF2" },
      false,
      ["deriveBits"]
    );
    const bits = await window.crypto.subtle.deriveBits(
      { name: "PBKDF2", salt: salt, iterations: 100000, hash: "SHA-256" },
      keyMaterial,
      256 // 32 bytes
    );
    return toHex(bits);
  }

  function pickEmail(form) {
    const emailField = form.querySelector('input[name="email"]');
    if (emailField && emailField.value) return emailField.value;
    // Change-password form has no email input — fall back to a data-attribute.
    if (form.dataset.email) return form.dataset.email;
    return "";
  }

  async function hashFields(form) {
    const email = pickEmail(form);
    const fieldNames = ["password", "current_password", "new_password"];
    for (const name of fieldNames) {
      const el = form.querySelector('input[name="' + name + '"]');
      if (!el) continue;
      const v = el.value;
      if (!v) continue;
      // Already a hex hash? skip.
      if (/^[a-f0-9]{64}$/.test(v)) continue;
      el.value = await deriveClientHash(v, email);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll("form[data-client-hash]");
    forms.forEach(function (form) {
      form.addEventListener("submit", async function (ev) {
        if (form.dataset._hashed === "1") return;
        ev.preventDefault();
        try {
          await hashFields(form);
          form.dataset._hashed = "1";
          form.submit();
        } catch (err) {
          form.dataset._hashed = "0";
          throw err;
        }
      });
    });
  });
})();
