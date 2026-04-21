// ============================
// INIT
// ============================
document.addEventListener("DOMContentLoaded", () => {

    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");

    if (!token || role !== "bapenda") {
        alert("Akses hanya untuk bapenda");
        window.location.href = "/index.html";
        return;
    }

    loadCafe();
    setupForm();
});


// ============================
// LOAD DATA (PREFILL)
// ============================
async function loadCafe() {

    const cafeId = localStorage.getItem("editCafe");

    if (!cafeId) {
        alert("Cafe tidak ditemukan");
        history.back();
        return;
    }

    try {
        const res = await fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
            headers: {
                Authorization: `Bearer ${localStorage.getItem("token")}`
            }
        });

        if (!res.ok) throw new Error("Gagal ambil data");

        const data = await res.json();

        // 🔥 isi form
        document.getElementById("name").value = data.name || "";
        document.getElementById("address").value = data.address || "";
        document.getElementById("open_time").value = data.open_time || "";
        document.getElementById("close_time").value = data.close_time || "";
        document.getElementById("table_count").value = data.table_count || "";
        document.getElementById("camera_count").value = data.camera_count || "";
        document.getElementById("username").value = data.username || "";

        // 🔥 title
        document.title = "Edit Cafe - " + data.name;

    } catch (err) {
        console.error("ERROR LOAD:", err);
        alert("Gagal load data cafe");
    }
}


// ============================
// SUBMIT FORM
// ============================
function setupForm() {

    const form = document.getElementById("editForm");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const cafeId = localStorage.getItem("editCafe");

        const payload = {
            name: document.getElementById("name").value,
            address: document.getElementById("address").value,
            open_time: document.getElementById("open_time").value,
            close_time: document.getElementById("close_time").value,
            table_count: document.getElementById("table_count").value,
            camera_count: document.getElementById("camera_count").value,
            username: document.getElementById("username").value,
            password: document.getElementById("password").value // opsional
        };

        try {
            const res = await fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${localStorage.getItem("token")}`
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (!res.ok) throw new Error(data.error || "Gagal update");

            alert("Cafe berhasil diupdate");

            window.location.href = "settings.html";

        } catch (err) {
            console.error("ERROR UPDATE:", err);
            alert(err.message);
        }
    });
}