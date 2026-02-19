import "./style.css";

let sidebar, mainContent, toggleIcon;

document.addEventListener("DOMContentLoaded", () => {
  sidebar = document.getElementById("sidebar");
  mainContent = document.getElementById("mainContent");
  toggleIcon = document.getElementById("toggleIcon");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const logoutBtn = document.getElementById("logoutBtn");
  const logoutModal = document.getElementById("logoutModal");
  const cancelLogout = document.getElementById("cancelLogout");
  const deleteAccountButtons = document.querySelectorAll("#deleteAccountButton");
  const deleteAccountModal = document.getElementById("deleteAccountModal");
  const cancelDeleteAccountButton = document.getElementById(
    "cancelDeleteAccountButton"
  );

  // --- LOGIKA MODAL LOGOUT (Dengan Pengecekan Aman) ---
  if (logoutBtn && logoutModal) {
    logoutBtn.addEventListener("click", () => {
      logoutModal.classList.remove("hidden");
      document.body.style.overflow = "hidden";
    });
  }

  if (cancelLogout && logoutModal) {
    cancelLogout.addEventListener("click", () => {
      logoutModal.classList.add("hidden");
      document.body.style.overflow = "auto";
    });
  }

  if (logoutModal) {
    logoutModal.addEventListener("click", (e) => {
      if (e.target.classList.contains("bg-black/40")) {
        // Cek klik pada overlay
        cancelLogout.click();
      }
    });
  }

  // --- LOGIKA MODAL HAPUS AKUN (Dengan Pengecekan Aman) ---
  deleteAccountButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (deleteAccountModal) {
        deleteAccountModal.classList.remove("hidden");
        document.body.style.overflow = "hidden";
      }
    });
  });

  if (cancelDeleteAccountButton && deleteAccountModal) {
    cancelDeleteAccountButton.addEventListener("click", () => {
      deleteAccountModal.classList.add("hidden");
      document.body.style.overflow = "auto";
    });
  }

  if (deleteAccountModal) {
    deleteAccountModal.addEventListener("click", (e) => {
      if (e.target.classList.contains("bg-black/40")) {
        // Cek klik pada overlay
        cancelDeleteAccountButton.click();
      }
    });
  }

  // --- LOGIKA SIDEBAR ---
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
        if (toggleIcon)
          toggleIcon.setAttribute("data-lucide", isHidden ? "menu" : "x");
      }
      if (window.lucide) lucide.createIcons();
    });
  }
  if (window.lucide) lucide.createIcons();
});

// Menangani perubahan ukuran layar (Resize)
window.addEventListener("resize", () => {
  // Pastikan variabel sudah terisi sebelum manipulasi
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

// --- LOGIKA DROPDOWN BULAN & TAHUN ---
const monthSelect = document.getElementById("monthSelect");
const yearSelect = document.getElementById("yearSelect");
const tahunSekarang = new Date().getFullYear(); // Mendapatkan tahun saat ini
const bulanSekarang = new Date().getMonth() + 1; // Mendapatkan bulan saat ini (0-11, jadi ditambah 1)

const bulan = [
  "Januari",
  "Februari",
  "Maret",
  "April",
  "Mei",
  "Juni",
  "Juli",
  "Agustus",
  "September",
  "Oktober",
  "November",
  "Desember",
];

// Isi Bulan
bulan.forEach((nama, index) => {
  let option = document.createElement("option");
  option.value = index + 1;
  option.textContent = nama;
  // Set default ke bulan saat ini
  if (nama === bulan[bulanSekarang - 1]) option.selected = true;

  monthSelect.appendChild(option);
});

// Menentukan rentang tahun (contoh: 5 tahun ke belakang hingga 2 tahun ke depan)
const tahunMulai = tahunSekarang - 10;
const tahunSelesai = tahunSekarang + 1;

for (let i = tahunMulai; i <= tahunSelesai; i++) {
  let option = document.createElement("option");
  option.value = i;
  option.textContent = i;

  // Set default ke tahun sekarang
  if (i === tahunSekarang) option.selected = true;

  yearSelect.appendChild(option);
}

// Fungsi untuk mendapatkan jumlah hari dalam bulan tertentu
function getDaysInMonth(month, year) {
  return new Date(year, month, 0).getDate();
}

// Inisialisasi Ikon Lucide
lucide.createIcons();
