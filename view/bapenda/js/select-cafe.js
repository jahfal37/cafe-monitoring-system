document.addEventListener("DOMContentLoaded", () => {
    loadCafes();
});

async function loadCafes() {
    try {
        const response = await fetch("http://127.0.0.1:5000/api/cafes");
        const cafes = await response.json();

        const container = document.getElementById("cafeList");
        container.innerHTML = "";

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
                            <span class="text-sm font-medium">${cafe.address}</span>
                        </div>

                        <div class="flex items-center gap-3 text-cafe-muted">
                            <i data-lucide="clock" class="w-5 h-5 text-cafe-primary"></i>
                            <span class="text-sm font-medium">
                                ${cafe.open_time} - ${cafe.close_time}
                            </span>
                        </div>

                        <div class="flex items-center gap-3 text-cafe-muted">
                            <i data-lucide="users" class="w-5 h-5 text-cafe-primary"></i>
                            <span class="text-sm font-medium">
                                ${cafe.table_count} meja
                            </span>
                        </div>

                        <div class="w-full mt-6 bg-slate-100 hover:bg-slate-200 text-cafe-dark font-bold py-3 rounded-xl transition-colors cursor-pointer text-center"
onclick="selectCafe('${cafe.id}')"
                            Lihat Dashboard
                        </div>
                    </div>
                </div>
            `;

            container.innerHTML += card;
        });

        // 🔥 WAJIB untuk icon dinamis
        lucide.createIcons();

    } catch (error) {
        console.error("Error:", error);
    }
}

function selectCafe(id) {
    localStorage.setItem("selectedCafe", id);
    window.location.href = "/view/bapenda/dashboard.html";
}