document.addEventListener("DOMContentLoaded", () => {

    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");

    // 🔒 proteksi login
    if (!token || role !== "bapenda") {
        alert("Akses hanya untuk bapenda");
        window.location.href = "/index.html";
        return;
    }

    loadCafes();

    // logout
    document.getElementById("logoutBtn")?.addEventListener("click", () => {
        localStorage.clear();
        window.location.href = "/index.html";
    });
});


// ============================
// LOAD DATA CAFE
// ============================
async function loadCafes() {
    try {

        const response = await fetch("http://127.0.0.1:5000/api/bapenda/cafes", {
            headers: {
                Authorization: `Bearer ${localStorage.getItem("token")}`
            }
        });

        if (!response.ok) {
            throw new Error("Gagal ambil data cafe");
        }

        const cafes = await response.json();

        const container = document.getElementById("cafeList");
        container.innerHTML = "";

        if (!cafes.length) {
            container.innerHTML = `
                <p class="text-center text-cafe-muted col-span-full">
                    Tidak ada data cafe
                </p>
            `;
            return;
        }

        cafes.forEach(cafe => {

            const card = `
                <div class="bg-white rounded-cafe shadow-cafe-card overflow-hidden border border-white transition-transform hover:scale-[1.02]">
                    
                    <div class="bg-linear-to-br from-cafe-primary to-cafe-accent p-8 text-white">
                        <i data-lucide="coffee" class="w-10 h-10 mb-4 opacity-80"></i>
                        <h2 class="text-2xl font-bold">${cafe.name}</h2>
                    </div>

                    <div class="p-8 space-y-4">

                        <div class="flex items-center gap-3 text-cafe-muted">
                            <i data-lucide="map-pin" class="w-5 h-5 text-cafe-primary"></i>
                            <span class="text-sm font-medium">
                                ${cafe.address || "-"}
                            </span>
                        </div>

                        <div class="flex items-center gap-3 text-cafe-muted">
                            <i data-lucide="clock" class="w-5 h-5 text-cafe-primary"></i>
                            <span class="text-sm font-medium">
                                ${cafe.open_time || "-"} - ${cafe.close_time || "-"}
                            </span>
                        </div>

                        <div class="flex items-center gap-3 text-cafe-muted">
                            <i data-lucide="users" class="w-5 h-5 text-cafe-primary"></i>
                            <span class="text-sm font-medium">
                                ${cafe.table_count || 0} meja
                            </span>
                        </div>

                        <button 
                            onclick="selectCafe('${cafe.id}')"
                            class="w-full mt-6 bg-slate-100 hover:bg-slate-200 text-cafe-dark font-bold py-3 rounded-xl transition-colors">
                            Lihat Dashboard
                        </button>

                    </div>
                </div>
            `;

            container.innerHTML += card;
        });

        lucide.createIcons();

    } catch (error) {
        console.error("ERROR:", error);
        alert("Gagal load data cafe");
    }
}


// ============================
// PILIH CAFE
// ============================
function selectCafe(id) {
    localStorage.setItem("selectedCafe", id);

    // redirect ke dashboard bapenda
    window.location.href = "/view/bapenda/dashboard.html";
}