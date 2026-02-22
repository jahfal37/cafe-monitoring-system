const API_BASE = "http://127.0.0.1:5000/api/devices";
const tbody = document.getElementById("deviceTableBody");

document.addEventListener("DOMContentLoaded", () => {
    loadDevices();
    loadStats();
});

async function loadDevices() {
    try {
        const response = await fetch(API_BASE);
        const devices = await response.json();

        const tbody = document.querySelector("tbody");
        tbody.innerHTML = "";

        devices.forEach(device => {
            const statusText =
                device.status === "active" ? "Aktif" : "Nonaktif";

            const statusClass =
                device.status === "active"
                    ? "bg-green-100 text-green-600"
                    : "bg-red-100 text-red-600";

            const row = `
                <tr>
                    <td>${device.device_code}</td>
                    <td class="text-center">
                        <span class="px-4 py-1 rounded-full ${statusClass}">
                            ${statusText}
                        </span>
                    </td>
                    <td class="text-center">
                        ${device.last_update}
                    </td>
                </tr>
            `;

            tbody.innerHTML += row;
        });

    } catch (error) {
        console.error("Gagal load devices:", error);
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();

        const statNumbers = document.querySelectorAll(".text-4xl");

        statNumbers[0].innerText = stats.total;
        statNumbers[1].innerText = stats.active;
        statNumbers[2].innerText = stats.inactive;

    } catch (error) {
        console.error("Gagal load stats:", error);
    }
}