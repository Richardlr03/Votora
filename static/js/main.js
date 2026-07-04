// Custom JS for Votora
console.log("Votora loaded");

function lockFormForSubmit(form, loadingText) {
  if (form.dataset.vpSubmitLocked === "true") {
    return false;
  }

  form.dataset.vpSubmitLocked = "true";
  form.classList.add("vp-form-locked");

  form.querySelectorAll("input, select, textarea").forEach(function (el) {
    const type = (el.type || "").toLowerCase();
    if (type === "submit" || type === "button" || type === "radio" || type === "checkbox") {
      return;
    }
    if (el.tagName === "SELECT") {
      return;
    }
    el.readOnly = true;
  });

  form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (btn) {
    btn.disabled = true;
    if (btn.tagName === "BUTTON") {
      btn.dataset.vpOriginalHtml = btn.innerHTML;
      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
        loadingText;
    } else {
      btn.dataset.vpOriginalValue = btn.value;
      btn.value = loadingText;
    }
  });

  return true;
}

// Auto-dismiss Bootstrap alerts after 3 seconds
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll("[data-vp-lock-on-submit]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (form.dataset.vpSubmitLocked === "true") {
        event.preventDefault();
        return;
      }

      const loadingText = form.getAttribute("data-vp-lock-on-submit") || "Submitting…";
      lockFormForSubmit(form, loadingText);
    });
  });

	var alerts = document.querySelectorAll('.alert.alert-dismissible.show');
	alerts.forEach(function (alert) {
		setTimeout(function () {
			var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
			bsAlert.close();
		}, 3000);
	});

	// Hide alerts that are visually associated with a form when the user starts typing.
	// This covers cases where the alert sits outside the <form> (e.g. above the form).
	document.querySelectorAll('form').forEach(function (form) {
		// listen on inputs inside the form
		var inputs = form.querySelectorAll('input, textarea, select');
		if (!inputs.length) return;

		var onFirstInput = function () {
			// Prefer a nearby container (card-body or the form's parent) to find related alerts
			var container = form.closest('.card-body') || form.parentElement || document;
			var relatedAlerts = container.querySelectorAll('.alert');
			relatedAlerts.forEach(function (alert) {
				try {
					var bs = bootstrap.Alert.getOrCreateInstance(alert);
					bs.close();
				} catch (e) {
					alert.remove();
				}
			});
		};

		inputs.forEach(function (input) {
			input.addEventListener('input', onFirstInput, { once: true });
		});
	});
});
