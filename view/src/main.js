import "./style.css";

document.addEventListener("DOMContentLoaded", () => {
  // ============================
  // AMBIL ELEMENT (SAFE)
  // ============================
  const sidebar = document.getElementById("sidebar");
  const mainContent = document.getElementById("mainContent");
  const toggleIcon = document.getElementById("toggleIcon");
  const sidebarToggle = document.getElementById("sidebarToggle");

  const logoutBtn = document.getElementById("logoutBtn");
  const logoutModal = document.getElementById("logoutModal");
  const cancelLogout = document.getElementById("cancelLogout");

  const deleteAccountButtons = document.querySelectorAll("#deleteAccountButton");
  const deleteAccountModal = document.getElementById("deleteAccountModal");
  const cancelDeleteAccountButton = document.getElementById("cancelDeleteAccountButton");

  const monthSelect = document.getElementById("monthSelect");
  const yearSelect = document.getElementById("yearSelect");

  // ============================
  // LOGOUT MODAL (SAFE)
  // ============================
  if (logoutBtn && logoutModal) {
    logoutBtn.addEventListener("click", () => {
      logoutModal.classList.remove("hidden");
      logoutModal.classList.add("flex");
      document.body.style.overflow = "hidden";
    });
  }

  if (cancelLogout && logoutModal) {
    cancelLogout.addEventListener("click", () => {
      logoutModal.classList.add("hidden");
      logoutModal.classList.remove("flex");
      document.body.style.overflow = "auto";
    });
  }

  if (logoutModal && cancelLogout) {
    logoutModal.addEventListener("click", (e) => {
      if (e.target.classList.contains("bg-black/40")) {
        cancelLogout.click();
      }
    });
  }

  // ============================
  // DELETE ACCOUNT MODAL (SAFE)
  // ============================
  if (deleteAccountButtons.length && deleteAccountModal) {
    deleteAccountButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        deleteAccountModal.classList.remove("hidden");
        document.body.style.overflow = "hidden";
      });
    });
  }

  if (cancelDeleteAccountButton && deleteAccountModal) {
    cancelDeleteAccountButton.addEventListener("click", () => {
      deleteAccountModal.classList.add("hidden");
      document.body.style.overflow = "auto";
    });
  }

  // ============================
  // SIDEBAR TOGGLE (SAFE)
  // ============================
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      const isMobile = window.innerWidth < 768;

      if (isMobile) {
        if (sidebar.classList.contains("h-0")) {
          sidebar.classList.replace("h-0", "h-fit");
          sidebar.classList.replace("opacity-0", "opacity-100");
          if (toggleIcon) toggleIcon.setAttribute("data-lucide", "x");
        } else {
          sidebar.classList.replace("h-fit", "h-0");
          sidebar.classList.replace("opacity-100", "opacity-0");
          if (toggleIcon) toggleIcon.setAttribute("data-lucide", "menu");
        }
      } else {
        sidebar.classList.toggle("md:w-72");
        sidebar.classList.toggle("md:w-0");
        sidebar.classList.toggle("md:opacity-100");
        sidebar.classList.toggle("md:opacity-0");

        if (mainContent) {
          mainContent.classList.toggle("md:ml-72");
          mainContent.classList.toggle("md:ml-0");
        }

        const isHidden = sidebar.classList.contains("md:w-0");
        if (toggleIcon) {
          toggleIcon.setAttribute("data-lucide", isHidden ? "menu" : "x");
        }
      }

      if (window.lucide) lucide.createIcons();
    });
  }

  // ============================
  // DROPDOWN BULAN & TAHUN (SAFE)
  // ============================
  if (monthSelect && yearSelect) {
    const tahunSekarang = new Date().getFullYear();
    const bulanSekarang = new Date().getMonth() + 1;

    const bulan = [
      "Januari", "Februari", "Maret", "April",
      "Mei", "Juni", "Juli", "Agustus",
      "September", "Oktober", "November", "Desember"
    ];

    // Isi bulan
    bulan.forEach((nama, index) => {
      const option = document.createElement("option");
      option.value = index + 1;
      option.textContent = nama;

      if (index + 1 === bulanSekarang) option.selected = true;

      monthSelect.appendChild(option);
    });

    // Isi tahun
    for (let i = tahunSekarang - 10; i <= tahunSekarang + 1; i++) {
      const option = document.createElement("option");
      option.value = i;
      option.textContent = i;

      if (i === tahunSekarang) option.selected = true;

      yearSelect.appendChild(option);
    }
  }

  // ============================
  // INIT ICON
  // ============================
  if (window.lucide) lucide.createIcons();
});


// ============================
// RESIZE HANDLER (SAFE)
// ============================
window.addEventListener("resize", () => {
  const sidebar = document.getElementById("sidebar");
  const mainContent = document.getElementById("mainContent");

  if (!sidebar || !mainContent) return;

  const isMobile = window.innerWidth < 768;

  if (!isMobile) {
    sidebar.classList.remove("h-0", "h-fit", "opacity-0");
    sidebar.classList.add("md:w-72", "md:opacity-100", "opacity-100");

    mainContent.classList.add("md:ml-72");
    mainContent.classList.remove("ml-0");
  } else {
    sidebar.classList.remove("md:w-72", "md:opacity-100", "h-fit");
    sidebar.classList.add("h-0", "opacity-0");

    mainContent.classList.remove("md:ml-72");
    mainContent.classList.add("ml-0");
  }

  if (window.lucide) lucide.createIcons();
});