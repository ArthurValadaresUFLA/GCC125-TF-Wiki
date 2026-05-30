document.addEventListener("DOMContentLoaded", () => {

    const sidebarToggle = document.querySelector("#sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }

    const searchInput = document.querySelector("#search-pages");

    if (searchInput) {

        searchInput.addEventListener("input", (event) => {

            const query = event.target.value.toLowerCase();

            document.querySelectorAll(".page-link")
                .forEach((item) => {

                    const text = item.innerText.toLowerCase();

                    item.style.display =
                        text.includes(query)
                            ? "flex"
                            : "none";
                });
        });
    }

});
