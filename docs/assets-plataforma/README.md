# Imagens da plataforma

Imagens que a própria plataforma mostra, no bucket público `eumini-assets`, carregadas direto pelo navegador ([ARQUITETURA §15](../ARQUITETURA.md#imagens-da-plataforma-bucket-público)).

## Categorias da home

| | |
|---|---|
| **Data** | 23/11/2026 |
| **Onde aparecem** | Na vitrine da home (`CategoryPicker`), no lugar dos ícones |
| **Arquivos** | `categorias/<categoria>-v1.webp`, 256 px, enviados para `categories/` do bucket |
| **Escolhidas** | `person-1`, `pet-1`, `couple-1`, `person_pet-1` |
| **Custo** | US$ 0,44 pelas 12 variações (foto e miniatura) |

### Como foram feitas

- **Fotos de entrada sintéticas:** cada foto foi gerada por texto na Runware, com pessoas e pets fictícios. Assim não há direito de imagem de ninguém na home.
- **Miniatura:** cada foto passou pelo prompt de produção (`catalog/prompts.py`, versão `2026-11-19`), na Runware, como o worker faz.
- **Escolha:** foram 3 variações por categoria. A folha com foto e miniatura lado a lado está em [`categorias/geracao/folha.jpg`](categorias/geracao/folha.jpg), e os prompts e custos em `categorias/geracao/resultado.json`.
- **Acabamento:** a margem branca foi recortada e a imagem ficou quadrada, em WebP de 256 px.

### Para trocar ou refazer

A partir da raiz:

```
apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_categorias.py gerar
apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_categorias.py finalizar person-1 pet-1 couple-1 person_pet-1
```

O cache dessas imagens é permanente. Para trocar uma imagem:

1. Suba a `VERSAO` no script e gere `-v2`.
2. Aponte `image()` em `apps/web/consumer/src/features/catalog/categories.ts` para o nome novo.
3. Depois do `aws login`, envie a partir de `apps/backend`:

```
.venv/Scripts/python.exe scripts/provision_s3.py --upload-assets
```

O bucket é o mesmo em todos os ambientes, então não há nada a fazer no lançamento.
