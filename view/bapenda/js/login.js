document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("loginForm");

    form.addEventListener("submit", function (e) {
        e.preventDefault();

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        fetch("http://127.0.0.1:5000/api/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        })
        .then(res => res.json())
        .then(data => {

            if (data.error) {
                alert(data.error);
                return;
            }

            // Simpan session login
            localStorage.setItem("cafe_id", data.cafe_id);
            localStorage.setItem("cafe_name", data.name);
            localStorage.setItem("role", data.role);

            console.log("ROLE DARI BACKEND:", data.role);

            // Redirect berdasarkan role
            if (data.role === "bapenda") {
                window.location.href = "view/bapenda/select-cafe.html";
            } else {
                window.location.href = "view/cafe/dashboard.html";
            }

        })
        .catch(err => {
            console.error(err);
            alert("Terjadi kesalahan server");
        });

    });

});