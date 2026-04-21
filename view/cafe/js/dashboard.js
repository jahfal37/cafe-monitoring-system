let myChart;
let intervalId;

// ============================
// HELPER INIT ICON
// ============================
function initIcons() {
    if (window.lucide) {
        lucide.createIcons();
    }
}

// ============================
// INIT
// ============================
document.addEventListener("DOMContentLoaded", () => {

    // 🔥 INIT ICON AWAL
    initIcons();

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
    const nameEl = document.getElementById("cafeName");
    if (cafeName && nameEl) {
        nameEl.innerText = cafeName;
    }

    // ✅ tampilkan alamat cafe
    const addressEl = document.getElementById("cafeAddress");
    if (cafeAddress && addressEl) {
        addressEl.innerText = cafeAddress;
    }

    // Load data
    loadCafeInfo();
    initFilter();
    loadDashboard();

    // 🔥 AUTO REFRESH (5 DETIK)
    intervalId = setInterval(loadDashboard, 5000);
});


// ============================
// INIT FILTER BULAN & TAHUN
// ============================
function initFilter() {
    const monthSelect = document.getElementById("monthSelect");
    const yearSelect = document.getElementById("yearSelect");

    if (!monthSelect || !yearSelect) return;

    monthSelect.innerHTML = "";
    yearSelect.innerHTML = "";

    const bulanList = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ];

    bulanList.forEach((nama, index) => {
        const option = document.createElement("option");
        option.value = index + 1;
        option.text = nama;
        monthSelect.appendChild(option);
    });

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

    const monthSelect = document.getElementById("monthSelect");
    const yearSelect = document.getElementById("yearSelect");

    if (!monthSelect || !yearSelect) return;

    const bulan = monthSelect.value;
    const tahun = yearSelect.value;

    fetch(`http://127.0.0.1:5000/api/cafe/dashboard?bulan=${bulan}&tahun=${tahun}`, {
        headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`
        }
    })
    .then(res => res.json())
    .then(data => {

        if (data.error) {
            alert(data.error);
            return;
        }

        // ============================
        // SET DATA
        // ============================
        const totalEl = document.getElementById("totalSaatIni");
        const rataEl = document.getElementById("rataRataBulan");
        const bulanEl = document.getElementById("trenPelangganBulan");
        const tahunEl = document.getElementById("trenPelangganTahun");

        if (totalEl) totalEl.innerText = data.total_saat_ini || 0;
        if (rataEl) rataEl.innerText = data.rata_rata_bulan || 0;
        if (bulanEl) bulanEl.innerText = data.bulan || "-";
        if (tahunEl) tahunEl.innerText = data.tahun || "-";

        // ============================
        // TABLE
        // ============================
        const tbody = document.querySelector("tbody");
        if (tbody) {
            tbody.innerHTML = "";

            if (data.data_harian && data.data_harian.length > 0) {
                data.data_harian.forEach(item => {
                    tbody.innerHTML += `
                        <tr>
                            <td class="px-4 md:px-8 py-4">${item.hari}</td>
                            <td class="px-4 md:px-8 py-4">${item.tanggal}</td>
                            <td class="px-4 md:px-8 py-4">${item.jumlah}</td>
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
        }

        // ============================
        // CHART
        // ============================
        const canvas = document.getElementById("trenChart");

        if (canvas) {
            const ctx = canvas.getContext("2d");

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
        }

        // 🔥 RE-INIT ICON SETELAH DOM UPDATE
        initIcons();

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

        const nameEl = document.getElementById("cafeName");
        const addressEl = document.getElementById("cafeAddress");
        const titleEl = document.getElementById("pageTitle");

        if (nameEl) nameEl.innerText = data.name || "-";
        if (addressEl) addressEl.innerText = data.address || "-";
        if (titleEl) titleEl.innerText = "Dashboard - " + data.name;

        localStorage.setItem("cafe_name", data.name);
        localStorage.setItem("cafe_address", data.address);

    })
    .catch(err => console.error("ERROR CAFE:", err));
}

// ============================
// STOP INTERVAL
// ============================
window.addEventListener("beforeunload", () => {
    if (intervalId) clearInterval(intervalId);
});