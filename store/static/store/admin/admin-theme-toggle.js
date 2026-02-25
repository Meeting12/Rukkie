(function () {
  var STORAGE_KEY = "rukkie_admin_theme";
  var STOREFRONT_THEME_ENDPOINT = "/api/storefront/theme/";
  var VALID_THEMES = ["default", "luxury-beauty", "obsidian-gold", "midnight", "sand", "forest", "ocean"];

  function isValidTheme(theme) {
    return VALID_THEMES.indexOf(theme) !== -1;
  }

  function applyTheme(theme) {
    var root = document.documentElement;
    var normalized = isValidTheme(theme) ? theme : "default";

    if (normalized === "default") {
      root.removeAttribute("data-rukkie-admin-theme");
      root.style.removeProperty("color-scheme");
      return;
    }

    root.setAttribute("data-rukkie-admin-theme", normalized);
    if (normalized === "midnight") {
      root.style.colorScheme = "dark";
    } else {
      root.style.colorScheme = "light";
    }
  }

  function getStoredTheme() {
    try {
      return window.localStorage.getItem(STORAGE_KEY) || "default";
    } catch (err) {
      return "default";
    }
  }

  function setStoredTheme(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (err) {
      // Ignore storage errors (private mode / policy).
    }
  }

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  function updateApplyButtonState(button, label, disabled) {
    if (!button) return;
    button.disabled = !!disabled;
    if (label) {
      button.textContent = label;
    }
  }

  function fetchStorefrontTheme() {
    return fetch(STOREFRONT_THEME_ENDPOINT, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        "Accept": "application/json"
      }
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("Failed to load storefront theme.");
      }
      return response.json().catch(function () { return {}; });
    });
  }

  function syncStorefrontTheme(theme) {
    var csrfToken = getCookie("csrftoken");
    return fetch(STOREFRONT_THEME_ENDPOINT, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify({ theme: theme || "default" })
    }).then(function (response) {
      if (!response.ok) {
        return response
          .json()
          .catch(function () { return {}; })
          .then(function (payload) {
            var detail = payload && (payload.detail || payload.error);
            throw new Error(detail || "Failed to update storefront theme.");
          });
      }
      return response.json().catch(function () { return {}; });
    });
  }

  function initThemeSelect() {
    var select = document.getElementById("rukkie-admin-theme-select");
    var applyButton = document.getElementById("rukkie-admin-theme-apply");
    if (!select) {
      return;
    }

    var current = getStoredTheme();
    if (!isValidTheme(current)) {
      current = "default";
    }

    select.value = current;
    applyTheme(current);

    function commitSelectedTheme() {
      var nextTheme = select ? select.value : "default";
      if (!isValidTheme(nextTheme)) {
        nextTheme = "default";
      }
      setStoredTheme(nextTheme);
      applyTheme(nextTheme);
      if (applyButton) {
        updateApplyButtonState(applyButton, "Applied", false);
        window.setTimeout(function () {
          updateApplyButtonState(applyButton, "Apply", false);
        }, 800);
      }
    }

    if (applyButton) {
      applyButton.addEventListener("click", commitSelectedTheme);
    }

    select.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        commitSelectedTheme();
      }
    });
  }

  function initStorefrontThemeSelect() {
    var select = document.getElementById("rukkie-storefront-theme-select");
    var applyButton = document.getElementById("rukkie-storefront-theme-apply");
    if (!select) {
      return;
    }

    function validStorefrontTheme(theme) {
      return theme === "default" || theme === "luxury-beauty" || theme === "obsidian-gold";
    }

    fetchStorefrontTheme()
      .then(function (payload) {
        var current = String((payload && payload.theme) || "default").toLowerCase();
        select.value = validStorefrontTheme(current) ? current : "default";
      })
      .catch(function () {
        select.value = "default";
      });

    function commitStorefrontTheme() {
      var nextTheme = select ? String(select.value || "default").toLowerCase() : "default";
      if (!validStorefrontTheme(nextTheme)) {
        nextTheme = "default";
      }
      if (applyButton) {
        applyButton.title = "";
        updateApplyButtonState(applyButton, "Applying...", true);
      }
      syncStorefrontTheme(nextTheme)
        .then(function () {
          if (applyButton) {
            updateApplyButtonState(applyButton, "Applied", false);
            window.setTimeout(function () {
              updateApplyButtonState(applyButton, "Apply", false);
            }, 1200);
          }
        })
        .catch(function (err) {
          if (applyButton) {
            updateApplyButtonState(applyButton, "Retry", false);
            applyButton.title = (err && err.message) ? err.message : "Storefront theme sync failed";
          }
        });
    }

    if (applyButton) {
      applyButton.addEventListener("click", commitStorefrontTheme);
    }
    select.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        commitStorefrontTheme();
      }
    });
  }

  function boot() {
    applyTheme(getStoredTheme());
    initThemeSelect();
    initStorefrontThemeSelect();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
