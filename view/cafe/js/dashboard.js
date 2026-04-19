let myChart;
let intervalId;

// ============================
// INIT
// ============================
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    const cafeId = localStorage.getItem("cafe_id");
    const cafeName = localStorage.getItem("cafe_name");
    const cafeAddress = localStorage.getItem("cafe_address");

    // 🔒 proteksi login
    if (!token || !cafeId) {
        alert("Silakan login terlebih dahulu");
        window.location.href = "/index.html";
        return;
    }

    // ✅ tampilkan nama cafe
    if (cafeName) {
        const nameEl = document.getElementById("cafeName");
        if (nameEl) nameEl.innerText = cafeName;
    }

    // ✅ tampilkan alamat cafe
    if (cafeAddress) {
        const addressEl = document.getElementById("cafeAddress");
        if (addressEl) addressEl.innerText = cafeAddress;
    }
    // Load Cafe Info
    loadCafeInfo();

    // 🔥 INIT DROPDOWN
    initFilter();

    // 🔥 LOAD AWAL
    loadDashboard();

    // 🔥 AUTO REFRESH (5 DETIK)
    intervalId = setInterval(() => {
        loadDashboard();
    }, 5000);
});


// ============================
// INIT FILTER BULAN & TAHUN
// ============================
function initFilter() {
    const monthSelect = document.getElementById("monthSelect");
    const yearSelect = document.getElementById("yearSelect");

    // 🔥 RESET DULU (INI YANG PENTING)
    monthSelect.innerHTML = "";
    yearSelect.innerHTML = "";

    const bulanList = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ];

    // isi bulan
    bulanList.forEach((nama, index) => {
        const option = document.createElement("option");
        option.value = index + 1;
        option.text = nama;
        monthSelect.appendChild(option);
    });

    // isi tahun
    for (let y = 2024; y <= 2026; y++) {
        const option = document.createElement("option");
        option.value = y;
        option.text = y;
        yearSelect.appendChild(option);
    }

    const now = new Date();
    monthSelect.value = now.getMonth() + 1;
    yearSelect.value = now.getFullYear();

    monthSelect.addEventListener("change", loadDashboard);
    yearSelect.addEventListener("change", loadDashboard);
}


// ============================
// LOAD DASHBOARD
// ============================
function loadDashboard() {

    const bulan = document.getElementById("monthSelect").value;
    const tahun = document.getElementById("yearSelect").value;

    console.log("REQUEST:", bulan, tahun);

    fetch(`http://127.0.0.1:5000/api/cafe/dashboard?bulan=${bulan}&tahun=${tahun}`, {
        headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`
        }
    })
    .then(res => res.json())
    .then(data => {

        console.log("RESPONSE:", data);

        if (data.error) {
            alert(data.error);
            return;
        }

        // ============================
        // SET DATA
        // ============================
        document.getElementById("totalSaatIni").innerText =
            data.total_saat_ini || 0;

        document.getElementById("rataRataBulan").innerText =
            data.rata_rata_bulan || 0;

        document.getElementById("trenPelangganBulan").innerText =
            data.bulan || "-";

        document.getElementById("trenPelangganTahun").innerText =
            data.tahun || "-";


        // ============================
        // TABLE
        // ============================
        const tbody = document.querySelector("tbody");
        tbody.innerHTML = "";

        if (data.data_harian && data.data_harian.length > 0) {
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


        // ============================
        // CHART
        // ============================
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
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

    })
    .catch(err => {
        console.error("ERROR:", err);
    });
}

// ============================
// LOAD CAFE INFO
// ============================
function loadCafeInfo() {
    const cafeId = localStorage.getItem("cafe_id");

    fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
        headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`
        }
    })
    .then(res => res.json())
    .then(data => {

        console.log("CAFE INFO:", data);

        // 🔥 update UI
        document.getElementById("cafeName").innerText = data.name || "-";
        document.getElementById("cafeAddress").innerText = data.address || "-";

        // 🔥 update title
        document.getElementById("pageTitle").innerText = "Dashboard - " + data.name;

        // 🔥 simpan ulang biar sinkron
        localStorage.setItem("cafe_name", data.name);
        localStorage.setItem("cafe_address", data.address);

    })
    .catch(err => console.error("ERROR CAFE:", err));
}

// ============================
// LOGOUT
// ============================
document.getElementById("logoutBtn")?.addEventListener("click", () => {
    localStorage.clear();
    window.location.href = "/index.html";
});


// ============================
// STOP INTERVAL
// ============================
window.addEventListener("beforeunload", () => {
    if (intervalId) clearInterval(intervalId);
});