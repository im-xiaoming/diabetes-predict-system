document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        const wrapper = button.closest(".relative");
        const input = wrapper ? wrapper.querySelector("input") : null;
        const icon = button.querySelector(".material-symbols-outlined");

        if (!input) {
            return;
        }

        button.addEventListener("click", () => {
            const isHidden = input.type === "password";

            input.type = isHidden ? "text" : "password";
            button.setAttribute("aria-label", isHidden ? "Ẩn mật khẩu" : "Hiện mật khẩu");

            if (icon) {
                icon.textContent = isHidden ? "visibility_off" : "visibility";
            }
        });
    });
});
