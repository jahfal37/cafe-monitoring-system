let intervalId;

// ============================
// INIT
// ============================
document.addEventListener("DOMContentLoaded", () => {

    const token = localStorage.getItem("token");
    const cafeName = localStorage.getItem("cafe_name");
    const cafeAddress = localStorage.getItem("cafe_address");

    if (!token) {
        alert("Silakan login terlebih dahulu");
        window.location.href = "/index.html";
        return;
    }

    // tampilkan nama cafe
    if (cafeName) document.querySelector("h2").innerText = cafeName;
    if (cafeAddress) document.querySelector("p").innerText = cafeAddress;

    loadDevices();

    // auto refresh tiap 5 detik
    intervalId = setInterval(loadDevices, 5000);
});


// ============================
// LOAD DEVICES
// ============================
function loadDevices() {

    fetch("http://127.0.0.1:5000/api/devices", {
        headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`
        }
    })
    .then(res => res.json())
    .then(data => {

        console.log("DEVICES:", data);

        // ======================
        // CARD
        // ======================
        const cards = document.querySelectorAll(".text-4xl");

        cards[0].innerText = data.total || 0;
        cards[1].innerText = data.active || 0;
        cards[2].innerText = data.inactive || 0;

        // ======================
        // TABLE
        // ======================
        const tbody = document.querySelector("tbody");
        tbody.innerHTML = "";

        if (!data.devices || data.devices.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center py-5">
                        Tidak ada perangkat
                    </td>
                </tr>
            `;
            return;
        }

        data.devices.forEach(device => {

            const statusClass =
                device.status === "active"
                    ? "bg-cafe-green-nonaktive text-cafe-green"
                    : "bg-cafe-red-nonaktive text-cafe-red";

            const statusText =
                device.status === "active" ? "Aktif" : "Nonaktif";

            const waktu = device.last_update
                ? new Date(device.last_update).toLocaleTimeString()
                : "-";

            const row = `
                <tr class="hover:bg-gray-50 transition-colors">
                    <td class="px-8 py-5 text-cafe-dark font-medium">${device.device_code}</td>
                    <td class="px-8 py-5 text-center">
                        <span class="px-6 py-1.5 rounded-full ${statusClass} text-sm font-bold">
                            ${statusText}
                        </span>
                    </td>
                    <td class="px-8 py-5 text-right text-cafe-muted">${waktu}</td>
                </tr>
            `;

            tbody.innerHTML += row;
        });

    })
    .catch(err => {
        console.error("ERROR DEVICES:", err);
    });
}


// ============================
// LOGOUT
// ============================
document.getElementById("logoutBtn")?.addEventListener("click", () => {
    localStorage.clear();
    window.location.href = "/index.html";
});


// ============================
// CLEAR INTERVAL
// ============================
window.addEventListener("beforeunload", () => {
    if (intervalId) clearInterval(intervalId);
});