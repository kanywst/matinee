# The tape CI records to prove the whole pipeline still works end to end.
#
# Deliberately tiny and dependency-free: it echoes, so it needs nothing built
# and finishes in seconds. Two section comments, so the run exercises chapter
# placement rather than just "a video came out".

Set Shell "bash"
Set FontSize 20
Set Width 900
Set Height 400
Set Padding 20
Set TypingSpeed 40ms
Set Theme "Catppuccin Mocha"
Set Framerate 24

# Say hello
Type "echo hello from matinee"
Sleep 300ms
Enter
Sleep 1500ms

# Say goodbye
Type "echo goodbye"
Sleep 300ms
Enter
# Long enough for the second chapter's narration to finish inside its own
# slot; tts.py warns when a line overruns, and an example should not.
Sleep 3500ms
