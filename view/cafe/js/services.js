let intervalId;

// ============================
// INIT
// ============================
document.addEventListener("DOMContentLoaded", () => {

    const token = localStorage.getItem("token");
    const cafeId = localStorage.getItem("cafe_id");
    const cafeName = localStorage.getItem("cafe_name");
    const cafeAddress = localStorage.getItem("cafe_address");

    if (!token || !cafeId) {
        alert("Silakan login terlebih dahulu");
        window.location.href = "/index.html";
        return;
    }

    // tampilkan nama & alamat cafe
        if (cafeName) document.querySelector("h2").innerText = cafeName;
        if (cafeAddress) document.querySelector("p").innerText = cafeAddress;

    const dateInput = document.querySelector("input[type='date']");
    const today = new Date().toISOString().split("T")[0];

    dateInput.value = today;

    loadServices(today);

    dateInput.addEventListener("change", () => {
        loadServices(dateInput.value);
    });

    intervalId = setInterval(() => {
        loadServices(dateInput.value);
    }, 5000);
});

// ============================
// LOAD CAMERAS
// ============================
async function loadCameras(cafeId) {
    const cafeId = localStorage.getItem("cafe_id");

    const res = await fetch(`http://localhost:5000/api/devices?cafe_id=${cafeId}`);
    const data = await res.json();

    renderCameras(data);
}

// ============================
// RENDER CAMERAS
// ============================
function renderCameras(cameras) {

    const container = document.getElementById("cameraGrid");
    container.innerHTML = "";

    if (!cameras || cameras.length === 0) {
        container.innerHTML = `
            <p class="text-gray-500">Tidak ada kamera tersedia</p>
        `;
        return;
    }

    cameras.forEach((cam, index) => {
        container.innerHTML += `
        <div class="bg-white rounded-cafe shadow-cafe-card p-4">
            <h3 class="font-bold text-cafe-dark mb-3">${cam.name}</h3>

            <div class="relative w-full h-[400px] bg-black rounded-xl overflow-hidden">
            <img src="${cam.stream_url}" class="w-full h-full object-cover" />

            <div class="absolute top-2 left-2 bg-red-600 text-white text-xs px-3 py-1 rounded">
                LIVE
            </div>
            </div>
        </div>
        `;
    });
}

// ============================
// LOAD DATA
// ============================
function loadServices(tanggal) {

    const token = localStorage.getItem("token");

    if (!token) {
        console.error("TOKEN TIDAK ADA");
        return;
    }

    console.log("TOKEN:", token);
    console.log("TANGGAL:", tanggal);

    fetch(`http://127.0.0.1:5000/api/services?tanggal=${tanggal}`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error("Gagal fetch services");
        }
        return res.json();
    })
    .then(data => {

        console.log("SERVICE DATA:", data);

        // ======================
        // CARD
        // ======================
        const cards = document.querySelectorAll(".text-4xl");

        cards[0].innerText = `${data.rata_rata || 0} Menit`;
        cards[1].innerText = `${data.terlama || 0} Menit`;
        cards[2].innerText = `${data.long_wait || 0} Kasus`;

        // ======================
        // TABLE
        // ======================
        const tbody = document.querySelector("tbody");
        tbody.innerHTML = "";

        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center py-5">
                        Tidak ada data
                    </td>
                </tr>
            `;
            return;
        }

        data.data.forEach((item) => {

            const statusClass =
                item.status === "long"
                    ? "bg-cafe-red-nonaktive text-cafe-red"
                    : "bg-cafe-green-nonaktive text-cafe-green";

            const statusText =
                item.status === "long" ? "Long wait" : "Normal";

            const row = `
                <tr>
                    <td class="px-6 py-5">${item.customer_code}</td>
                    <td class="px-6 py-5">${item.table_number}</td>
                    <td class="px-6 py-5">${item.waiting_time} Menit</td>
                    <td class="px-6 py-5 text-center">
                        <span class="px-6 py-1.5 rounded-full ${statusClass} text-sm font-bold">
                            ${statusText}
                        </span>
                    </td>
                </tr>
            `;

            tbody.innerHTML += row;
        });

    })
    .catch(err => {
        console.error("ERROR SERVICES:", err);
    });
}

// ============================
// CLEAR INTERVAL
// ============================
window.addEventListener("beforeunload", () => {
    if (intervalId) clearInterval(intervalId);
});