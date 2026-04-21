let myChart;

// ============================
// INIT
// ============================
document.addEventListener("DOMContentLoaded", () => {

    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");

    if (!token || role.trim() !== "bapenda") {
        alert("Akses hanya untuk bapenda");
        window.location.href = "/index.html";
        return;
    }

    initFilter();
    loadCafeDropdown();
    loadCafeInfo();
    loadDashboard();

    // logout
    const logoutBtn = document.getElementById("logoutBtn");
const logoutModal = document.getElementById("logoutModal");
const cancelLogout = document.getElementById("cancelLogout");
const confirmLogout = document.getElementById("confirmLogout");

if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
        logoutModal.classList.remove("hidden");
        logoutModal.classList.add("flex");
    });
}

if (cancelLogout) {
    cancelLogout.addEventListener("click", () => {
        logoutModal.classList.add("hidden");
        logoutModal.classList.remove("flex");
    });
}

if (confirmLogout) {
    confirmLogout.addEventListener("click", () => {
        localStorage.clear();
        window.location.href = "/index.html";
    });
}


// ============================
// DROPDOWN CAFE
// ============================
async function loadCafeDropdown() {
    const select = document.getElementById("cafeSelect");

    try {
        const res = await fetch("http://127.0.0.1:5000/api/bapenda/cafes", {
            headers: {
                Authorization: `Bearer ${localStorage.getItem("token")}`
            }
        });

        const cafes = await res.json();

        select.innerHTML = `<option value="">Pilih Cafe</option>`;

        cafes.forEach(cafe => {
            select.innerHTML += `
                <option value="${cafe.id}">${cafe.name}</option>
            `;
        });

        // default dari halaman sebelumnya
        const selected = localStorage.getItem("selectedCafe");
        if (selected) {
            select.value = selected;
        }

        select.addEventListener("change", () => {
            localStorage.setItem("selectedCafe", select.value);
            loadCafeInfo();
            loadDashboard();
        });

    } catch (err) {
        console.error("ERROR DROPDOWN:", err);
    }
}


// ============================
// FILTER BULAN & TAHUN
// ============================
function initFilter() {
    const month = document.getElementById("monthSelect");
    const year = document.getElementById("yearSelect");

    month.innerHTML = "";
    year.innerHTML = "";

    const bulan = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ];

    bulan.forEach((b, i) => {
        month.innerHTML += `<option value="${i+1}">${b}</option>`;
    });

    for (let y = 2024; y <= 2026; y++) {
        year.innerHTML += `<option value="${y}">${y}</option>`;
    }

    const now = new Date();
    month.value = now.getMonth() + 1;
    year.value = now.getFullYear();

    month.addEventListener("change", loadDashboard);
    year.addEventListener("change", loadDashboard);
}


// ============================
// LOAD DASHBOARD
// ============================
async function loadDashboard() {

    const cafeId = localStorage.getItem("selectedCafe");
    const bulan = document.getElementById("monthSelect").value;
    const tahun = document.getElementById("yearSelect").value;

    if (!cafeId) {
        console.log("Belum pilih cafe");
        return;
    }

    try {
        const res = await fetch(
            `http://127.0.0.1:5000/api/bapenda/dashboard/${cafeId}?bulan=${bulan}&tahun=${tahun}`,
            {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem("token")}`
                }
            }
        );

        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        // =========================
        // SET DATA
        // =========================
        document.getElementById("totalSaatIni").innerText = data.total_saat_ini || 0;
        document.getElementById("rataRataBulan").innerText = data.rata_rata_bulan || 0;
        document.getElementById("trenPelangganBulan").innerText = data.bulan || "-";
        document.getElementById("trenPelangganTahun").innerText = data.tahun || "-";

        // =========================
        // TABLE
        // =========================
        const tbody = document.querySelector("tbody");
        tbody.innerHTML = "";

        if (data.data_harian?.length > 0) {
            data.data_harian.forEach(item => {
                tbody.innerHTML += `
                    <tr>
                        <td>${item.hari}</td>
                        <td>${item.tanggal}</td>
                        <td>${item.jumlah}</td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center py-4">
                        Tidak ada data
                    </td>
                </tr>
            `;
        }

        // =========================
        // CHART (SMOOTH)
        // =========================
        const ctx = document.getElementById("trenChart").getContext("2d");

        if (myChart) myChart.destroy();

        myChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: data.data_harian?.map(d => d.tanggal) || [],
                datasets: [{
                    label: "Jumlah Pelanggan",
                    data: data.data_harian?.map(d => d.jumlah) || [],
                    borderColor: "#F9B208",
                    backgroundColor: "rgba(249,178,8,0.1)",
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1000,
                    easing: "easeInOutQuart"
                },
                plugins: {
                    legend: {
                        labels: {
                            color: "#333",
                            font: { size: 14 }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: "#666" },
                        grid: { display: false }
                    },
                    y: {
                        ticks: { color: "#666" },
                        grid: { color: "#eee" }
                    }
                }
            }
        });

    } catch (err) {
        console.error("ERROR DASHBOARD:", err);
    }
}


// ============================
// LOAD INFO CAFE
// ============================
async function loadCafeInfo() {

    const cafeId = localStorage.getItem("selectedCafe");

    if (!cafeId) return;

    try {
        const res = await fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
            headers: {
                Authorization: `Bearer ${localStorage.getItem("token")}`
            }
        });

        const data = await res.json();

        console.log("INFO CAFE:", data);

        document.getElementById("cafeName").innerText = data.name || "-";
        document.getElementById("cafeAddress").innerText = data.address || "-";

        document.title = "Dashboard - " + data.name;

    } catch (err) {
        console.error("ERROR LOAD CAFE:", err);
    }
}