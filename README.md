# PDV Online Automation

Framework de automação de testes para um sistema de **PDV (Ponto de Venda) online**, cobrindo três frentes:

| Frente | Tecnologias | O que valida |
|---|---|---|
| **API** | `requests` + `pytest` + JSON Schema | Status HTTP, estrutura/tipos do JSON, regras de negócio, mensagens de erro |
| **UI** | `Selenium` + Page Object Model | Login, produtos, clientes e fluxo completo de venda no navegador |
| **Fiscal** | `lxml` | XML de NFC-e: estrutura, dados e consistência aritmética |

O projeto é executável de ponta a ponta sem nenhum sistema externo: ele traz um **PDV de demonstração** (`demo_app/`) que a suíte sobe sozinha.

> ⚠️ **Dados fictícios.** O `demo_app`, os produtos, CNPJ, chaves de acesso, NCM, CFOP, CST e alíquotas dos XMLs em `test_data/` são **inventados apenas para testes**. Não representam uma empresa real, nem regras fiscais oficiais, e os XMLs **não são documentos fiscais válidos perante a SEFAZ**.

## Objetivos

- Servir como portfólio de QA/Automação com padrões próximos aos da indústria.
- Ser fácil de clonar, instalar e executar (`pip install` + `pytest`).
- Facilitar a adição de novos testes: nova página = nova classe em `src/pages/`; novo endpoint = nova classe em `src/api/`.
- Poder ser apontado para outro PDV apenas trocando as variáveis do `.env`.

## Tecnologias

Python 3.12+ · pytest · pytest-html · Selenium 4 (Selenium Manager gerencia o driver) · requests · lxml · jsonschema · python-dotenv · Flask (somente o app de demonstração) · GitHub Actions.

## Arquitetura

```
UI:      Teste → Page Object → Selenium → Browser → PDV (demo_app) → asserts → relatório
API:     Teste → API Client  → HTTP     → API     → Response       → asserts → relatório
NFC-e:   Teste → XmlValidator → XML → validação estrutural → de dados → de consistência → asserts
```

Decisões relevantes:

- **`demo_app/` com Flask serve UI e API**, em memória. Por isso `BASE_URL` e `API_URL` apontam para o mesmo processo, e a UI de vendas usa a mesma API testada em `tests/api`. A pasta se chama `demo_app` (e não `demo-app`) porque hífen impede `import`.
- **A suíte sobe o demo_app automaticamente** (fixture de sessão `demo_server`) quando nada responde em `BASE_URL/health`. Se já houver um sistema rodando, ele é reutilizado. Testes fiscais não iniciam servidor nem navegador.
- **Configuração em um só lugar** (`config/settings.py`), lida de variáveis de ambiente / `.env`. Não há credenciais no código.
- **Seletores só nas Page Objects.** Os testes não importam Selenium.
- **O validador fiscal devolve `ValidationIssue(layer, code, location, message)`**, não strings. Os testes afirmam `report.has("INVALID_CNPJ", "emit/CNPJ")`, sem depender do texto da mensagem.
- **Setup via API em testes de UI** (`created_product`): cria dados de forma rápida e determinística, e remove ao final.

## Estrutura de pastas

```
pdv-online-automation/
├── .github/workflows/tests.yml   # CI: jobs api, fiscal e ui
├── config/settings.py            # configuração centralizada (.env)
├── demo_app/                     # PDV de demonstração (Flask) – UI + API REST
├── src/
│   ├── api/                      # ApiClient + AuthAPI/ProductsAPI/CustomersAPI/SalesAPI + schemas JSON
│   ├── pages/                    # Page Objects (BasePage, Login, Dashboard, Products, Customers, Sales)
│   ├── models/                   # Product, Customer, SaleItem (+ builders de dados únicos)
│   └── utils/                    # logger, xml_validator, helpers, driver_factory, demo_server
├── tests/
│   ├── api/                      # test_login, test_products, test_customers, test_sales
│   ├── ui/                       # test_login, test_products, test_customers, test_sales
│   └── fiscal/test_nfce_xml.py
├── test_data/                    # users.json, products.json, nfce/valid_nfce.xml, nfce/invalid_nfce.xml
├── reports/                      # report.html, junit.xml, screenshots/   (gerado, ignorado pelo Git)
├── logs/                         # test_execution.log                      (gerado, ignorado pelo Git)
├── conftest.py                   # fixtures e hooks (screenshot, logging, relatório)
├── pytest.ini                    # markers e opções padrão
├── requirements.txt
└── .env.example
```

## Instalação

Requer Python 3.12+ e Chrome instalado (para os testes de UI).

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Depois:

```bash
pip install -r requirements.txt
```

## Configuração

Copie o arquivo de exemplo e ajuste se necessário. O `.env` real está no `.gitignore`.

```bash
cp .env.example .env
```

| Variável | Descrição | Padrão do exemplo |
|---|---|---|
| `BASE_URL` | URL base da interface web | `http://127.0.0.1:5055` |
| `API_URL` | URL base da API (se omitida: `BASE_URL/api`) | `http://127.0.0.1:5055/api` |
| `TEST_USERNAME` / `TEST_PASSWORD` | Credenciais usadas pelos testes (e como usuário válido do demo_app) | valores de demonstração |
| `BROWSER` | `chrome` ou `firefox` | `chrome` |
| `HEADLESS` | `true` em CI, `false` para ver o navegador | `true` |
| `START_DEMO_APP` | Sobe o demo_app se nada responder em `BASE_URL` | `true` |
| `TIMEOUT` | Timeout (s) de esperas do Selenium e requisições HTTP | `10` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` | `INFO` |

Sem `.env` (ou sem `TEST_USERNAME`/`TEST_PASSWORD`), o pytest aborta com uma mensagem indicando o que falta.

Para apontar para outro sistema: ajuste `BASE_URL`, `API_URL` e credenciais, e defina `START_DEMO_APP=false`. Os seletores e contratos de `src/pages` e `src/api` foram escritos para o demo_app e precisarão ser adaptados.

Para explorar o demo_app manualmente: `python -m demo_app` e abra `http://127.0.0.1:5055`.

## Executando os testes

```bash
pytest                  # tudo
pytest -m api           # testes de API
pytest -m ui            # testes de UI (abre o navegador; use HEADLESS=false para acompanhar)
pytest -m fiscal        # validação de XML de NFC-e
pytest -m smoke         # fluxos críticos, rápido
pytest -m regression    # regressão completa
pytest -m "api and smoke"
pytest tests/fiscal -k cnpj
```

Markers: `api`, `ui`, `fiscal`, `smoke`, `regression` (registrados em `pytest.ini`, com `--strict-markers`: marker com erro de digitação falha na coleta). Todos os testes são `regression`; um subconjunto é também `smoke`.

Ordem de grandeza: ~215 testes; API e fiscal levam poucos segundos, UI leva alguns minutos (um navegador por teste, para isolamento).

## Relatórios, logs e screenshots

| Artefato | Caminho |
|---|---|
| Relatório HTML (autocontido) | `reports/report.html` |
| JUnit XML | `reports/junit.xml` |
| Screenshots de falhas de UI | `reports/screenshots/<nome_do_teste>_<data_hora>.png` (e embutido no HTML) |
| Log de execução | `logs/test_execution.log` |

O log registra início/fim de cada teste (com resultado), cada chamada de API (método, URL, status, tempo), ações importantes da UI, erros com traceback e o resultado da validação de XML.
O relatório é gerado mesmo quando há falhas.

## Page Object Model

Cada tela é uma classe em `src/pages/` que **encapsula seletores e interações**. O teste descreve *o quê*; a página sabe *como*:

```python
def test_login_success(login_page, dashboard_page, settings):
    login_page.open()
    login_page.login(settings.username, settings.password)
    assert dashboard_page.is_loaded()
```

Por quê: se um seletor muda, corrige-se em um lugar; os testes ficam curtos e legíveis; o código de espera/sincronização (`BasePage`) é reaproveitado. Dois cuidados importantes na `BasePage`: **esperas explícitas** (nenhum `sleep`) e `_click_and_wait_navigation`, que só retorna depois que o documento antigo foi substituído, evitando condições de corrida em submits de formulário.

## Estratégia de testes de API

- `ApiClient` concentra sessão, timeout, token e logging; `ProductsAPI`, `CustomersAPI` e `SalesAPI` expõem uma operação por método e **devolvem a `Response` crua** — assertivas ficam nos testes.
- `src/api/schemas.py` define o contrato (JSON Schema) para validar campos obrigatórios e tipos; `assert_schema` produz mensagens de falha legíveis.
- Cenários positivos e negativos: credenciais inválidas/ausentes, produto sem nome / preço inválido / código duplicado, venda com produto inexistente, quantidade inválida, carrinho vazio, acesso sem token.
- Casos negativos vêm de `test_data/*.json` e rodam via `pytest.mark.parametrize`.
- Dados criados pelos testes usam códigos únicos (`Product.build()`), então podem rodar repetidamente contra o mesmo ambiente.

## Validação de NFC-e

`src/utils/xml_validator.py` (`NFCeValidator`, baseado em `lxml`) separa três camadas:

1. **Estrutural** – existem `infNFe/@Id`, `ide` (mod, série, nNF, dhEmi), `emit/CNPJ`, ao menos um `det` com `cProd`, `xProd`, `NCM`, `CFOP`, `uCom`, `qCom`, `vUnCom`, `vProd`, e os grupos de `ICMS` (CST ou CSOSN), `PIS` e `COFINS` por item, além de `vProd`/`vNF` em `ICMSTot`.
2. **De dados** – chave de acesso com 44 dígitos e DV (módulo 11) correto; CNPJ com dígitos verificadores; modelo 65; série e número em formato válido; `dhEmi` ISO 8601 **com fuso**; quantidades/valores numéricos e positivos; NCM com 8 dígitos; CFOP com 4; formato de CST/CSOSN; impostos não negativos.
3. **De consistência** – `qCom × vUnCom ≈ vProd` (por item), soma dos itens ≈ `vProd` total, `vNF ≈ vProd − vDesc + vOutro`, base × alíquota ≈ valor de ICMS/PIS/COFINS, e a chave de acesso coerente com CNPJ, modelo, série, número e AAMM da nota. A **tolerância é de R$ 0,01**, por causa do arredondamento de cada valor para 2 casas (ex.: 1,5 × 4,99 = 7,485 → 7,49).

Observações honestas sobre o escopo:

- É validação de **qualidade de dados para testes**, não substitui a validação oficial por XSD/assinatura/SEFAZ. Só há regras objetivas e verificáveis; nenhuma regra tributária (alíquotas, ST, CFOP × CST permitidos etc.) foi inventada.
- A regra `vNF = vProd − vDesc + vOutro` é uma **simplificação deliberada** (não considera ST, frete, seguro etc.).
- O parser desabilita resolução de entidades e acesso à rede (proteção contra XXE) – XML de entrada é tratado como não confiável.

Arquivos de exemplo:

- `test_data/nfce/valid_nfce.xml` – 3 itens, regime normal (CST), passa nas três camadas.
- `test_data/nfce/invalid_nfce.xml` – bem formado, porém com defeitos catalogados no comentário do próprio arquivo (DV da chave, CNPJ, NCM ausente, CFOP curto, totais divergentes etc.).
- XML **mal formado** é testado com bytes em memória (`test_malformed_xml_is_rejected`).
- Os demais cenários negativos usam a função `mutate()` do teste: parte do XML válido e altera **um** campo, deixando claro qual regra cada teste exercita.

## CI/CD (GitHub Actions)

`.github/workflows/tests.yml` roda em **push** e **pull_request**, com três jobs independentes e paralelos:

| Job | Comando | Observações |
|---|---|---|
| `api` | `pytest -m api` | demo_app sobe automaticamente |
| `fiscal` | `pytest -m fiscal` | sem servidor nem navegador |
| `ui` | `pytest -m ui` | Chrome via `browser-actions/setup-chrome`, `HEADLESS=true` |

Cada job instala Python 3.12 (com cache do pip), executa os testes e, **mesmo em caso de falha** (`if: always()`), faz upload de `reports/` (HTML, JUnit, screenshots) e `logs/` como artefatos.
As credenciais no workflow são valores de demonstração do demo_app; para um sistema real, use *GitHub Secrets*.

## Melhorias futuras

- Playwright como alternativa/complemento ao Selenium.
- Docker / docker-compose (demo_app + runner de testes).
- Allure Report para relatórios com histórico e anexos.
- Banco de dados de teste com *seed* e *reset* entre execuções.
- Execução paralela (`pytest-xdist`) — hoje os testes são independentes, mas o demo_app é em memória e compartilhado.
- Testes de performance (Locust/k6) sobre a API de vendas.
- Integração com Jira/Xray para rastrear resultados em casos de teste.
- Testes de contrato (Pact / OpenAPI) em vez de somente schemas locais.
- Matriz de múltiplos navegadores no CI (`BROWSER=firefox` já é aceito pelo `driver_factory`, mas ainda não é exercitado no pipeline).
- Validação de NFC-e contra os XSD oficiais.

## Licença

MIT — veja [LICENSE](LICENSE).
