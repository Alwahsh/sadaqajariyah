/* Gate the "Schedule with me →" link behind the consent checkbox.
 *
 * The link is rendered with `aria-disabled="true"` and a `.is-locked` class
 * so it visually appears disabled before this JS runs and from clients with
 * JS disabled (the click is also blocked here for the JS-enabled case).
 */
(function () {
  "use strict";

  function bindConsent(link) {
    var key = link.getAttribute("data-consent-target");
    if (!key) return;
    var checkbox = document.querySelector('[data-consent="' + key + '"]');
    if (!checkbox) return;
    var hint = document.querySelector('[data-test="' + key + '-hint"]');
    var beforeText = hint ? hint.getAttribute("data-locked-text") || hint.textContent : "";
    var afterText = hint ? hint.getAttribute("data-unlocked-text") || "Opens in a new tab" : "";

    function update() {
      if (checkbox.checked) {
        link.classList.remove("is-locked");
        link.removeAttribute("aria-disabled");
        if (hint) {
          hint.textContent = afterText;
          hint.classList.remove("is-warning");
        }
      } else {
        link.classList.add("is-locked");
        link.setAttribute("aria-disabled", "true");
        if (hint) {
          hint.textContent = beforeText;
          hint.classList.add("is-warning");
        }
      }
    }

    link.addEventListener("click", function (event) {
      if (!checkbox.checked) {
        event.preventDefault();
        // Surface the gate to the user — focus the checkbox and flash the hint.
        checkbox.focus({ preventScroll: false });
        if (hint) {
          hint.classList.remove("is-flash");
          // Trigger a reflow so the same class re-application animates.
          void hint.offsetWidth;
          hint.classList.add("is-flash");
        }
      }
    });

    checkbox.addEventListener("change", update);
    update();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var links = document.querySelectorAll("[data-consent-target]");
    for (var i = 0; i < links.length; i++) {
      bindConsent(links[i]);
    }
  });
})();
