document.addEventListener("DOMContentLoaded", () => {

    const logoutBtn = document.getElementById("logoutBtn");
    const logoutModal = document.getElementById("logoutModal");
    const cancelLogout = document.getElementById("cancelLogout");
    const confirmLogout = document.getElementById("confirmLogout");

    // OPEN MODAL
    if (logoutBtn && logoutModal) {
        logoutBtn.addEventListener("click", () => {
            logoutModal.classList.remove("hidden");
            logoutModal.classList.add("flex");
        });
    }

    // CANCEL
    if (cancelLogout && logoutModal) {
        cancelLogout.addEventListener("click", () => {
            logoutModal.classList.add("hidden");
            logoutModal.classList.remove("flex");
        });
    }

    // CONFIRM LOGOUT
    if (confirmLogout) {
        confirmLogout.addEventListener("click", () => {
            localStorage.clear();
            window.location.href = "/index.html";
        });
    }

    // CLICK OUTSIDE MODAL
    if (logoutModal) {
        logoutModal.addEventListener("click", (e) => {
            if (e.target === logoutModal) {
                logoutModal.classList.add("hidden");
                logoutModal.classList.remove("flex");
            }
        });
    }

});