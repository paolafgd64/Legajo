(function () {
  const themedClass = {
    popup: 'legajo-swal-popup',
    title: 'legajo-swal-title',
    htmlContainer: 'legajo-swal-html',
    confirmButton: 'legajo-swal-confirm',
    denyButton: 'legajo-swal-deny',
    cancelButton: 'legajo-swal-cancel',
    input: 'legajo-swal-input'
  };

  function themeOptions(options) {
    if (!options || typeof options !== 'object' || options.customClass) {
      return options;
    }

    return {
      buttonsStyling: false,
      customClass: themedClass,
      ...options
    };
  }

  function patchSwal() {
    if (!window.Swal || window.Swal.__legajoThemed) {
      return;
    }

    const originalFire = window.Swal.fire.bind(window.Swal);
    window.Swal.fire = function (...args) {
      if (args.length === 1 && typeof args[0] === 'object') {
        args[0] = themeOptions(args[0]);
      }
      return originalFire(...args);
    };
    window.Swal.__legajoThemed = true;
  }

  patchSwal();
})();
