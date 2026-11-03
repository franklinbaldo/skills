// Apoio à consulta do APPG (https://www.tjro.jus.br/appg/pages/index.xhtml),
// rodado na aba do APPG pelo Claude in Chrome (`javascript_tool`).
//
// NÃO resolve nem contorna o reCAPTCHA: quem marca "Não sou um robô" é a
// pessoa. O script preenche a Pesquisa Avançada, confere se o CAPTCHA está
// resolvido (grecaptcha.getResponse) e só então clica em Consultar e devolve
// o texto do resultado. Sem CAPTCHA, devolve {estado: "aguardando_captcha"}
// com o formulário já preenchido. O desafio vence em 2 minutos.
//
// Uso (cole o arquivo e chame no fim):
//   await appg({comarca: "Presidente Médici", tipo: "Número Processo Antigo", parametro: "00620010001382"})
//   await appg({comarca: "Presidente Médici", tipo: "Nome da Parte", parametro: "NORSEGEL", baixados: true})
//
// Tipos aceitos pela tela: "Nome da Parte", "Nome do Advogado",
// "Número Processo Antigo" (14 dígitos, FFFAAAASSSSSSD, sem pontuação),
// "OAB do Advogado", "Documento da Parte".

async function appg({ comarca, tipo, parametro, baixados = true }) {
  const espera = (ms) => new Promise((r) => setTimeout(r, ms));
  const id = (s) => document.getElementById(s);
  const COMARCA = "formNovo:idarc:strCodigoComarca";
  const TIPO = "formNovo:idarc:strTpConsulta";
  const PARAM = "formNovo:idarc:parametroConsulta";

  const escolher = async (campo, rotulo) => {
    const sel = id(campo);
    const opt = [...sel.options].find((o) => o.text.trim().toLowerCase() === rotulo.trim().toLowerCase());
    if (!opt) throw new Error(`opção não encontrada em ${campo}: ${rotulo}`);
    if (sel.value !== opt.value) {
      sel.value = opt.value;
      sel.dispatchEvent(new Event("change", { bubbles: true }));
      await espera(1500); // a página reconstrói o formulário por AJAX
    }
  };

  // A troca do tipo reconstrói o formulário e devolve a comarca ao padrão:
  // tipo primeiro, comarca depois, e confere os dois no fim.
  await escolher(TIPO, tipo);
  await escolher(COMARCA, comarca);
  const p = id(PARAM);
  p.value = parametro;
  p.dispatchEvent(new Event("change", { bubbles: true }));

  // Checkbox do PrimeFaces: o <input> fica escondido; clica-se na caixa visível.
  const caixa = id("formNovo:idarc:sbcbxBaixados_input");
  if (caixa && caixa.checked !== baixados) {
    id("formNovo:idarc:sbcbxBaixados").querySelector(".ui-chkbox-box").click();
    await espera(500);
  }

  const formulario = {
    comarca: id(COMARCA).selectedOptions[0]?.text,
    tipo: id(TIPO).selectedOptions[0]?.text,
    parametro: id(PARAM).value,
    baixados: caixa ? caixa.checked : null,
  };
  const token = window.grecaptcha?.getResponse?.() || "";
  if (!token) return { estado: "aguardando_captcha", formulario };

  const botao = [...document.querySelectorAll("button,input[type=submit]")].find(
    (b) => /Consultar/.test(b.innerText || b.value || "") && b.offsetParent !== null
  );
  botao.click();
  for (let i = 0; i < 20; i++) {
    await espera(1000);
    const carregando = [...document.querySelectorAll(".ui-dialog")].some(
      (d) => d.offsetParent !== null && /Processando/.test(d.innerText)
    );
    if (!carregando) break;
  }
  const mensagens = [...document.querySelectorAll(".ui-messages, .ui-message, .ui-growl")]
    .map((m) => m.innerText.trim())
    .filter(Boolean);
  const tabelas = [...document.querySelectorAll(".ui-datatable")]
    .filter((t) => t.offsetParent !== null)
    .map((t) => t.innerText.trim());
  return { estado: "consultado", formulario, mensagens, resultado: tabelas };
}
