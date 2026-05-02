// ============================
// INIT
// ============================
document.addEventListener("DOMContentLoaded", () => {

    const token = localStorage.getItem("token");
    const cafeId = localStorage.getItem("cafe_id");

    if (!token || !cafeId) {
        alert("Silakan login terlebih dahulu");
        window.location.href = "/index.html";
        return;
    }

    loadData(cafeId);

    document.getElementById("editForm")
        .addEventListener("submit", (e) => updateData(e, cafeId));

    document.getElementById("btnCancel")
        ?.addEventListener("click", () => history.back());

    document.getElementById("btnBack")
        ?.addEventListener("click", () => history.back());

    document.getElementById("addCameraBtn")
        ?.addEventListener("click", addCamera);
});


// ============================
// STATE
// ============================
let cameras = [];


// ============================
// LOAD DATA
// ============================
function loadData(cafeId) {

    fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
        headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`
        }
    })
    .then(res => res.json())
    .then(data => {

        document.getElementById("name").value = data.name || "";
        document.getElementById("address").value = data.address || "";
        document.getElementById("open_time").value = data.open_time || "";
        document.getElementById("close_time").value = data.close_time || "";
        document.getElementById("table_count").value = data.table_count || "";
        document.getElementById("username").value = data.username || "";
        document.getElementById("password").value = "";

        cameras = data.devices || data.cameras || [];

        renderCameras();
    })
    .catch(err => {
        console.error(err);
        alert("Gagal load data");
    });
}


// ============================
// RENDER CAMERA
// ============================
function renderCameras() {

    const container = document.getElementById("cameraContainer");
    container.innerHTML = "";

    if (cameras.length === 0) {
        container.innerHTML = `<p class="text-gray-500">Belum ada kamera</p>`;
        return;
    }

    cameras.forEach((cam, index) => {

        container.innerHTML += `
        <div class="border p-4 rounded-xl space-y-3 bg-gray-50">

            <div class="flex justify-between items-center">
                <h4 class="font-bold">Kamera ${index + 1}</h4>

                <button type="button"
                    onclick="removeCamera(${index})"
                    class="text-red-500 text-sm">
                    Hapus
                </button>
            </div>

            <input
                value="${cam.name || ""}"
                onchange="updateCamera(${index}, 'name', this.value)"
                class="w-full px-3 py-2 border rounded"
                placeholder="Nama Kamera" />

            <input
                value="${cam.stream_url || ""}"
                onchange="updateCamera(${index}, 'stream_url', this.value)"
                class="w-full px-3 py-2 border rounded"
                placeholder="Stream URL" />

        </div>
        `;
    });
}


// ============================
// ADD CAMERA
// ============================
function addCamera() {
    cameras.push({
        id: null,
        name: "",
        stream_url: ""
    });

    renderCameras();
}


// ============================
// UPDATE CAMERA FIELD
// ============================
window.updateCamera = (index, field, value) => {
    cameras[index][field] = value;
};


// ============================
// REMOVE CAMERA
// ============================
window.removeCamera = (index) => {
    cameras.splice(index, 1);
    renderCameras();
};


// ============================
// UPDATE DATA
// ============================
async function updateData(e, cafeId) {
    e.preventDefault();

    const token = localStorage.getItem("token");

    const payload = {
        name: document.getElementById("name").value,
        address: document.getElementById("address").value,
        open_time: document.getElementById("open_time").value,
        close_time: document.getElementById("close_time").value,
        table_count: document.getElementById("table_count").value,
        username: document.getElementById("username").value
    };

    const password = document.getElementById("password").value;
    if (password) payload.password = password;

    try {

        // =====================
        // UPDATE CAFE
        // =====================
        const res = await fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: "Bearer " + token
            },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            alert(err.error || "Gagal update cafe");
            return;
        }

        // =====================
        // SYNC CAMERAS
        // =====================
        for (const cam of cameras) {

            if (cam.id) {
                await fetch(`http://127.0.0.1:5000/api/devices/${cam.id}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: "Bearer " + token
                    },
                    body: JSON.stringify(cam)
                });
            } else {
                await fetch(`http://127.0.0.1:5000/api/devices`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: "Bearer " + token
                    },
                    body: JSON.stringify({
                        cafe_id: cafeId,
                        name: cam.name,
                        stream_url: cam.stream_url,
                        device_code: "CAM_NEW"
                    })
                });
            }
        }

        alert("Update berhasil");
        window.location.href = "dashboard.html";

    } catch (err) {
        console.error(err);
        alert("Error update data");
    }
}