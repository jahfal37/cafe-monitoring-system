let myChart;
let selectedCafeId;

window.addEventListener("load", function () {

    selectedCafeId = localStorage.getItem("selectedCafe");

    if (!selectedCafeId) {
        alert("Cafe belum dipilih");
        window.location.href = "select-cafe.html";
        return;
    }

    const monthSelect = document.getElementById("monthSelect");
    const yearSelect = document.getElementById("yearSelect");

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

    loadDashboard();
});

function loadDashboard() {

    const bulan = document.getElementById("monthSelect").value;
    const tahun = document.getElementById("yearSelect").value;

    fetch(`http://127.0.0.1:5000/api/dashboard?cafe_id=${selectedCafeId}&bulan=${bulan}&tahun=${tahun}`)
        .then(res => res.json())
        .then(data => {

            if (data.error) {
                alert(data.error);
                return;
            }

            document.getElementById("totalSaatIni").innerText = data.total_saat_ini;
            document.getElementById("rataRataBulan").innerText = data.rata_rata_bulan;
            document.getElementById("trenPelangganBulan").innerText = data.bulan;
            document.getElementById("trenPelangganTahun").innerText = data.tahun;

            const tbody = document.querySelector("tbody");
            tbody.innerHTML = "";

            data.data_harian.forEach(item => {
                tbody.innerHTML += `
                    <tr>
                        <td>${item.hari}</td>
                        <td>${item.tanggal}</td>
                        <td>${item.jumlah}</td>
                    </tr>
                `;
            });

            const ctx = document.getElementById('trenChart').getContext('2d');

            if (myChart) myChart.destroy();

            myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.data_harian.map(d => d.tanggal),
                    datasets: [{
                        label: "Jumlah Pelanggan",
                        data: data.data_harian.map(d => d.jumlah),
                        borderColor: '#F9B208',
                        backgroundColor: 'rgba(249,178,8,0.1)',
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
        .catch(err => console.error("Error:", err));
}