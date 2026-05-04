/* Inline formset enhancement: add / remove rows on the profile-edit
 * "Services you offer" formset.
 *
 * Required DOM:
 *   - <div data-formset-rows data-formset-prefix="X" data-max="N">
 *     - 0..N <div data-formset-row> ... </div>
 *   - <button data-formset-add>
 *   - <template data-formset-empty>...</template>
 *   - hidden management form input named "{prefix}-TOTAL_FORMS"
 *
 * Each row contains a hidden DELETE input (data-formset-delete) — the Remove
 * button sets it to "1" and hides the row visually. New rows added via the
 * button clone the <template> contents, replace __prefix__ with the next
 * index, and bump TOTAL_FORMS.
 */
(function () {
  "use strict";

  function init() {
    var container = document.querySelector("[data-formset-rows]");
    if (!container) return;
    var prefix = container.getAttribute("data-formset-prefix");
    var maxNum = parseInt(container.getAttribute("data-max") || "12", 10);
    var totalInput = document.querySelector(
      'input[name="' + prefix + '-TOTAL_FORMS"]'
    );
    var template = document.querySelector("template[data-formset-empty]");
    var addBtn = document.querySelector("[data-formset-add]");
    if (!totalInput || !template || !addBtn) return;

    function visibleRows() {
      return container.querySelectorAll(
        '[data-formset-row]:not([data-removed="1"])'
      );
    }

    function syncAddButton() {
      var atMax = visibleRows().length >= maxNum;
      if (atMax) {
        addBtn.setAttribute("disabled", "disabled");
        addBtn.setAttribute("aria-disabled", "true");
      } else {
        addBtn.removeAttribute("disabled");
        addBtn.removeAttribute("aria-disabled");
      }
    }

    function bindRemove(row) {
      var btn = row.querySelector("[data-formset-remove]");
      if (!btn) return;
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        var del = row.querySelector('[data-formset-delete]');
        if (del) del.value = "1";
        // Clear category to avoid required-field validation on a removed row.
        var cat = row.querySelector('select[name$="-category"]');
        if (cat) cat.value = "";
        row.setAttribute("data-removed", "1");
        row.style.display = "none";
        syncAddButton();
      });
    }

    function addRow() {
      if (visibleRows().length >= maxNum) return;
      var idx = parseInt(totalInput.value, 10);
      var src = template.content.firstElementChild;
      if (!src) return;
      // Render the template HTML with __prefix__ replaced by the next index.
      var html = src.outerHTML.split("__prefix__").join(String(idx));
      var wrap = document.createElement("div");
      wrap.innerHTML = html;
      var newRow = wrap.firstElementChild;
      bindRemove(newRow);
      container.appendChild(newRow);
      totalInput.value = String(idx + 1);
      syncAddButton();
      // Move keyboard focus to the new category select.
      var cat = newRow.querySelector('select[name$="-category"]');
      if (cat) cat.focus();
    }

    addBtn.addEventListener("click", function (ev) {
      ev.preventDefault();
      addRow();
    });

    var initialRows = container.querySelectorAll("[data-formset-row]");
    for (var i = 0; i < initialRows.length; i++) bindRemove(initialRows[i]);
    syncAddButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
