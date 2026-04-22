document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("loginForm");

    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    const usernameError = document.getElementById("usernameError");
    const passwordError = document.getElementById("passwordError");

    const loginButton = document.getElementById("loginButton");
    const btnText = document.getElementById("btnText");
    const btnSpinner = document.getElementById("btnSpinner");

    function showError(input, errorEl, message) {
        input.classList.add("input-error");
        errorEl.textContent = message;
        errorEl.classList.remove("hidden");
    }

    function clearError(input, errorEl) {
        input.classList.remove("input-error");
        errorEl.textContent = "";
        errorEl.classList.add("hidden");
    }

    function setLoading(isLoading) {
        if (isLoading) {
            loginButton.disabled = true;
            btnText.textContent = "Loading...";
            btnSpinner.classList.remove("hidden");
        } else {
            loginButton.disabled = false;
            btnText.textContent = "Sign In";
            btnSpinner.classList.add("hidden");
        }
    }

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        let isValid = true;

        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        clearError(usernameInput, usernameError);
        clearError(passwordInput, passwordError);

        if (!username) {
            showError(usernameInput, usernameError, "Username wajib diisi");
            isValid = false;
        }

        if (!password) {
            showError(passwordInput, passwordError, "Password wajib diisi");
            isValid = false;
        }

        if (!isValid) return;

        setLoading(true);

        try {
            const res = await fetch("http://localhost:5000/api/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ username, password })
            });

            const text = await res.text();

            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                showError(passwordInput, passwordError, "Response server tidak valid");
                return;
            }

            if (!res.ok || data.error) {
                showError(passwordInput, passwordError, data.error || "Login gagal");
                return;
            }

            // SUCCESS
            localStorage.setItem("token", data.access_token);
            localStorage.setItem("cafe_id", data.user.id);
            localStorage.setItem("role", data.user.role);
            localStorage.setItem("user_name", data.user.name);

            if (data.user.role === "cafe") {
                window.location.href = "/view/cafe/dashboard.html";
            } else {
                window.location.href = "/view/bapenda/select-cafe.html";
            }

        } catch (err) {
            console.error(err);
            showError(passwordInput, passwordError, "Server error, coba lagi");
        } finally {
            setLoading(false); // penting: selalu reset
        }
    });

    usernameInput.addEventListener("input", () => {
        clearError(usernameInput, usernameError);
    });

    passwordInput.addEventListener("input", () => {
        clearError(passwordInput, passwordError);
    });
});