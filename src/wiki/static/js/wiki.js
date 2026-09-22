// Comportamento mínimo da wiki. Sem dependências e sem scripts inline (compatível com a CSP).
(() => {
  "use strict";

  /** Força o carregamento de imagens "lazy" e espera que estejam prontas. */
  const loadAllImages = () =>
    Promise.all(
      Array.from(document.images, (image) => {
        image.loading = "eager";
        return image.decode().catch(() => undefined); // imagem quebrada não trava a impressão
      }),
    );

  // Qualquer impressão (Ctrl+P incluso) deve incluir as imagens que ainda não rolaram na tela.
  window.addEventListener("beforeprint", () => {
    for (const image of document.images) image.loading = "eager";
  });

  // Botões "Imprimir / salvar como PDF".
  for (const button of document.querySelectorAll("[data-print]")) {
    button.addEventListener("click", () => window.print());
  }
})();
