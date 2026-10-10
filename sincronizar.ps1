# Mantém esta pasta igual ao GitHub (branch main): puxa as alterações de 60 em 60 segundos.
# Uso (PowerShell, dentro da pasta do projeto):   .\sincronizar.ps1
# Para parar: Ctrl+C.
# Se der erro de permissões:   Set-ExecutionPolicy -Scope Process Bypass
#
# Atenção: só puxa (git pull). Se editares ficheiros aqui, faz commit e push antes,
# senão o pull pode recusar-se a correr para não perder o teu trabalho.
git checkout main
while ($true) {
    $saida = git pull --ff-only origin main 2>&1
    $hora = Get-Date -Format "HH:mm:ss"
    if ($saida -match "Already up to date") { Write-Host "[$hora] sem novidades" }
    else { Write-Host "[$hora] atualizado:`n$saida" }
    Start-Sleep -Seconds 60
}
