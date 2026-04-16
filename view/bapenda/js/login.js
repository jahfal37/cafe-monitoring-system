document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("loginForm");

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        try {
            const res = await fetch("http://127.0.0.1:5000/api/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username,
                    password
                })
            });

            const data = await res.json();

            if (data.error) {
                alert(data.error);
                return;
            }

            localStorage.setItem("token", data.access_token);
            localStorage.setItem("cafe_id", data.user.id);
            localStorage.setItem("role", data.user.role);
            localStorage.setItem("user_name", data.user.name);

            if (data.user.role === "cafe") {
                window.location.href = "/view/cafe/dashboard.html";
            } else if (data.user.role === "bapenda") {
                window.location.href = "view/bapenda/select-cafe.html";
            }

        } catch (err) {
            console.error(err);
            alert("Terjadi kesalahan server");
        }
    });
});