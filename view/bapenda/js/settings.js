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

    loadCafes();
    loadCafeInfo(); // 🔥 untuk navbar & title
});


// ============================
// LOAD DATA CAFE (TABLE)
// ============================
async function loadCafes() {

    try {
        const res = await fetch("http://127.0.0.1:5000/api/cafes", {
            headers: {
                Authorization: `Bearer ${localStorage.getItem("token")}`
            }
        });

        if (!res.ok) throw new Error("Gagal load cafes");

        const cafes = await res.json();

        const tbody = document.getElementById("cafeTableBody");

        if (!tbody) {
            console.error("cafeTableBody tidak ditemukan");
            return;
        }

        tbody.innerHTML = "";

        // 🔥 filter hanya role cafe (exclude bapenda)
        cafes
            .filter(cafe => cafe.role === "cafe")
            .forEach(cafe => {

                tbody.innerHTML += `
                    <tr class="hover:bg-gray-50 transition-colors">
                        
                        <td class="px-8 py-5 text-cafe-dark font-semibold">
                            ${cafe.name || "-"}
                        </td>

                        <td class="px-8 py-5 text-center">
                            <span class="px-6 py-1.5 rounded-full bg-gray-100 text-sm font-bold">
                                ${cafe.address || "-"}
                            </span>
                        </td>

                        <td class="px-4 md:px-8 py-5 text-center">
                            <div class="flex gap-3 justify-center items-center">

                                <button onclick="editCafe('${cafe.id}')"
                                    class="bg-cafe-green hover:bg-green-600 text-white font-bold px-4 py-2 rounded-xl shadow-lg transition-all">
                                    Edit
                                </button>

                                <button onclick="deleteCafe('${cafe.id}')"
                                    class="bg-cafe-red hover:bg-red-600 text-white font-bold px-4 py-2 rounded-xl shadow-lg transition-all">
                                    Hapus
                                </button>

                            </div>
                        </td>

                    </tr>
                `;
            });

    } catch (err) {
        console.error("ERROR LOAD CAFES:", err);
        alert("Gagal load data cafe");
    }
}


// ============================
// EDIT CAFE
// ============================
function editCafe(id) {
    localStorage.setItem("editCafe", id);
    window.location.href = "edit-cafe.html";
}


// ============================
// DELETE CAFE
// ============================
async function deleteCafe(id) {

    if (!confirm("Yakin ingin hapus cafe ini?")) return;

    try {
        const res = await fetch(`http://127.0.0.1:5000/api/cafes/${id}`, {
            method: "DELETE",
            headers: {
                Authorization: `Bearer ${localStorage.getItem("token")}`
            }
        });

        const data = await res.json();

        alert(data.message || "Berhasil dihapus");

        loadCafes(); // 🔥 refresh tabel

    } catch (err) {
        console.error("ERROR DELETE:", err);
        alert("Gagal hapus cafe");
    }
}


// ============================
// LOAD INFO CAFE (NAVBAR)
// ============================
async function loadCafeInfo() {

    const cafeId = localStorage.getItem("selectedCafe");

    // 🔥 fallback kalau belum pilih cafe
    if (!cafeId) {
        const nameEl = document.getElementById("cafeName");
        const addressEl = document.getElementById("cafeAddress");

        if (nameEl) nameEl.innerText = "Bapenda";
        if (addressEl) addressEl.innerText = "-";

        document.title = "Settings - Bapenda";
        return;
    }

    try {
        const res = await fetch(`http://127.0.0.1:5000/api/cafes/${cafeId}`, {
            headers: {
                Authorization: `Bearer ${localStorage.getItem("token")}`
            }
        });

        if (!res.ok) throw new Error("Gagal ambil cafe");

        const data = await res.json();

        const nameEl = document.getElementById("cafeName");
        const addressEl = document.getElementById("cafeAddress");

        if (nameEl) nameEl.innerText = data.name || "-";
        if (addressEl) addressEl.innerText = data.address || "-";

        document.title = "Settings - " + (data.name || "Cafe");

    } catch (err) {
        console.error("ERROR LOAD CAFE:", err);
    }
}