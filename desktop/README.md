# Fabuloom Studio Desktop

O Desktop é uma casca nativa fina sobre o `EngineService`. Ele não possui um
renderizador, catálogo ou pipeline de áudio paralelo: projetos, biblioteca,
jobs e validações usam os mesmos serviços da CLI e da API local.

## Desenvolvimento

```powershell
$env:PYTHONPATH = "$PWD\src"
python .\desktop\fabuloom_desktop.py --check
python .\desktop\fabuloom_desktop.py
```

O botão `Abrir Stage` inicia o servidor local já existente em loopback e abre
a interface web. O botão `Music Studio` abre a mesma aplicação no módulo de
música. A API estruturada compartilhada pode ser iniciada sem interface:

```powershell
python -m fabuloom_core.cli api --port 8790
```

PySide6/Tauri não estavam disponíveis na auditoria e não foram instalados.
Por isso, o primeiro Desktop utiliza Tkinter, disponível na distribuição
Python do Windows, mantendo a decisão reversível e sem duplicar o motor.
