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
});


// ============================
// LOAD DATA
// ============================
function loadData(cafeId) {

    console.log("CAFE ID:", cafeId);

    fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
        headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`
        }
    })
    .then(res => {
        console.log("STATUS:", res.status);

        if (!res.ok) {
            throw new Error("Gagal ambil data: " + res.status);
        }

        return res.json();
    })
    .then(data => {

        console.log("DATA CAFE:", data);

        document.getElementById("name").value = data.name || "";
        document.getElementById("address").value = data.address || "";
        document.getElementById("open_time").value = data.open_time || "";
        document.getElementById("close_time").value = data.close_time || "";
        document.getElementById("table_count").value = data.table_count || "";
        document.getElementById("camera_count").value = data.camera_count || "";
        document.getElementById("username").value = data.username || "";

    })
    .catch(err => {
        console.error("ERROR LOAD:", err);
        alert(err.message);
    });
}

// ============================
// UPDATE DATA
// ============================
function updateData(e, cafeId) {
    e.preventDefault();

    const payload = {
        name: document.getElementById("name").value,
        address: document.getElementById("address").value,
        open_time: document.getElementById("open_time").value,
        close_time: document.getElementById("close_time").value,
        table_count: document.getElementById("table_count").value,
        camera_count: document.getElementById("camera_count").value,
        username: document.getElementById("username").value,
        password: document.getElementById("password").value
    };

    fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(response => {

        console.log("UPDATE RESPONSE:", response);

        if (response.error) {
            alert(response.error);
            return;
        }

        alert("Data berhasil diupdate");

        // update nama di localStorage
        localStorage.setItem("cafe_name", payload.name);

        window.location.href = "dashboard.html";
    })
    .catch(err => {
        console.error("ERROR UPDATE:", err);
        alert("Gagal update data");
    });
}