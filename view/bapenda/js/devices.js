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

    loadCafeInfo();
    loadDevices();

    
});


// ============================
// LOAD DEVICES
// ============================
async function loadDevices() {

    const cafeId = localStorage.getItem("selectedCafe");

    if (!cafeId) {
        alert("Pilih cafe terlebih dahulu");
        window.location.href = "/view/bapenda/select-cafe.html";
        return;
    }

    try {

        const res = await fetch(
            `http://127.0.0.1:5000/api/bapenda/devices/${cafeId}`,
            {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem("token")}`
                }
            }
        );

        if (!res.ok) throw new Error("Response bukan OK");

        const data = await res.json();

        console.log("DEVICES:", data);

        // =========================
        // SET SUMMARY (AMAN)
        // =========================
        const totalEl = document.getElementById("totalCamera");
const activeEl = document.getElementById("activeCamera");
const inactiveEl = document.getElementById("inactiveCamera");

if (totalEl) totalEl.innerText = data.total ?? 0;
if (activeEl) activeEl.innerText = data.active ?? 0;
if (inactiveEl) inactiveEl.innerText = data.inactive ?? 0;
        // =========================
        // TABLE
        // =========================
        const tbody = document.getElementById("deviceTableBody");

        if (!tbody) {
            console.error("deviceTableBody tidak ditemukan di HTML");
            return;
        }

        tbody.innerHTML = "";

        if (!data.devices || data.devices.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center py-6 text-cafe-muted">
                        Tidak ada perangkat
                    </td>
                </tr>
            `;
            return;
        }

        data.devices.forEach((device, index) => {

            const isActive = device.status === "active";

            tbody.innerHTML += `
                <tr>
                    <td class="px-8 py-4 font-semibold">
                        Kamera ${index + 1}
                    </td>
                    <td class="px-8 py-4 text-center ${isActive ? "text-green-500" : "text-red-500"} font-bold">
                        ${isActive ? "Aktif" : "Nonaktif"}
                    </td>
                   <td class="px-8 py-4 text-center text-sm text-black whitespace-nowrap font-semibold">
    ${
        device.last_update 
        ? new Date(device.last_update).toLocaleString("id-ID") 
        : "-"
    }
</td>
                </tr>
            `;
        });

    } catch (err) {
        console.error("ERROR DEVICES:", err);
        alert("Gagal load perangkat");
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

        if (!res.ok) throw new Error("Gagal ambil cafe");

        const data = await res.json();

        console.log("CAFE:", data);

        const nameEl = document.getElementById("cafeName");
        const addressEl = document.getElementById("cafeAddress");

        if (nameEl) nameEl.innerText = data.name || "-";
        if (addressEl) addressEl.innerText = data.address || "-";

        document.title = "Devices - " + (data.name || "Cafe");

    } catch (err) {
        console.error("ERROR CAFE:", err);
    }
}