// AudioTranscriber.exe - starts AudioTranscriber. Never fails silently: every problem shows a message.
//
//	AudioTranscriber.exe            start the app (offers Repair if setup isn't complete)
//	AudioTranscriber.exe --tray     start hidden in the tray (used by "Start with Windows")
//	AudioTranscriber.exe --repair   open Repair (Setup.exe in the same folder)
//	AudioTranscriber.exe --debug    start with a console window (also: hold Shift while opening)
//
// Setup and Repair are done by Setup.exe (the installer keeps a copy of itself in the app folder).
// No PowerShell is used anywhere.
//
// Build (from this folder, any OS with Go 1.22+ and mingw windres):
//
//	x86_64-w64-mingw32-windres --preprocessor=cpp --preprocessor-arg=-P -i res.rc -O coff -o rsrc_windows_amd64.syso
//	GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags "-H windowsgui -s -w" -o AudioTranscriber.exe .
package main

import (
	"bufio"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

const (
	appName          = "AudioTranscriber"
	createNoWindow   = 0x08000000
	createNewConsole = 0x00000010

	mbOK            = 0x00000000
	mbYesNo         = 0x00000004
	mbIconError     = 0x00000010
	mbIconQuestion  = 0x00000020
	mbIconWarning   = 0x00000030
	mbSetForeground = 0x00010000
	idYes           = 6
	vkShift         = 0x10
)

var (
	user32           = syscall.NewLazyDLL("user32.dll")
	procMessageBoxW  = user32.NewProc("MessageBoxW")
	procGetKeyState  = user32.NewProc("GetAsyncKeyState")
	kernel32         = syscall.NewLazyDLL("kernel32.dll")
	procCreateMutexW = kernel32.NewProc("CreateMutexW")
	shell32          = syscall.NewLazyDLL("shell32.dll")
	procShellExecW   = shell32.NewProc("ShellExecuteW")
)

func messageBox(text string, flags uintptr) int {
	t, _ := syscall.UTF16PtrFromString(text)
	c, _ := syscall.UTF16PtrFromString(appName)
	r, _, _ := procMessageBoxW.Call(0, uintptr(unsafe.Pointer(t)), uintptr(unsafe.Pointer(c)), flags|mbSetForeground)
	return int(r)
}

func shiftHeld() bool {
	r, _, _ := procGetKeyState.Call(vkShift)
	return r&0x8000 != 0
}

func exists(p string) bool {
	_, err := os.Stat(p)
	return err == nil
}

// missing lists what the app needs and isn't there (empty = ready to start).
func missing(root string) []string {
	var out []string
	for _, p := range []string{
		`.venv\Scripts\pythonw.exe`,
		`.venv\Scripts\python.exe`,
		`.venv\Lib\site-packages\PySide6`,
		`.venv\Lib\site-packages\faster_whisper`,
		`app\main.py`,
	} {
		if !exists(filepath.Join(root, p)) {
			out = append(out, p)
		}
	}
	return out
}

// openRepair starts Setup.exe /REPAIR (the installer's repair mode) and returns at once.
func openRepair(root string) bool {
	setup := filepath.Join(root, "Setup.exe")
	if !exists(setup) {
		messageBox("Setup.exe is missing from the AudioTranscriber folder.\n\nRun AudioTranscriber_Setup.exe again and choose Repair.", mbOK|mbIconError)
		return false
	}
	verb, _ := syscall.UTF16PtrFromString("open")
	file, _ := syscall.UTF16PtrFromString(setup)
	args, _ := syscall.UTF16PtrFromString("/REPAIR")
	dir, _ := syscall.UTF16PtrFromString(root)
	r, _, _ := procShellExecW.Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(file)),
		uintptr(unsafe.Pointer(args)), uintptr(unsafe.Pointer(dir)), 1)
	if r <= 32 {
		messageBox("Repair could not be opened (error "+itoa(int(r))+").\n\nRun AudioTranscriber_Setup.exe again and choose Repair.", mbOK|mbIconError)
		return false
	}
	return true
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	s := ""
	neg := n < 0
	if neg {
		n = -n
	}
	for n > 0 {
		s = string(rune('0'+n%10)) + s
		n /= 10
	}
	if neg {
		s = "-" + s
	}
	return s
}

func logTail(root string, n int) string {
	f, err := os.Open(filepath.Join(root, "audiotranscriber.log"))
	if err != nil {
		return ""
	}
	defer f.Close()
	var lines []string
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 64*1024), 1024*1024)
	for sc.Scan() {
		lines = append(lines, sc.Text())
		if len(lines) > n {
			lines = lines[1:]
		}
	}
	out := strings.Join(lines, "\n")
	if len(out) > 1400 {
		out = "..." + out[len(out)-1400:]
	}
	return out
}

// launch starts the app. ok=false if it could not start or closed straight away with an error.
func launch(root, exe string, fwd []string, debug bool) (bool, string) {
	main := filepath.Join(root, "app", "main.py")
	env := append(os.Environ(), "AUDIOTRANSCRIBER_LAUNCHER="+exe)
	if debug {
		py := filepath.Join(root, ".venv", "Scripts", "python.exe")
		line := `cmd.exe /k ""` + py + `" "` + main + `"`
		for _, a := range fwd {
			line += ` "` + a + `"`
		}
		line += `"`
		cmd := exec.Command(filepath.Join(os.Getenv("SystemRoot"), `System32\cmd.exe`))
		cmd.SysProcAttr = &syscall.SysProcAttr{CmdLine: line, CreationFlags: createNewConsole}
		cmd.Dir, cmd.Env = root, append(env, "PYTHONUNBUFFERED=1")
		if err := cmd.Start(); err != nil {
			return false, err.Error()
		}
		return true, ""
	}
	cmd := exec.Command(filepath.Join(root, ".venv", "Scripts", "pythonw.exe"), append([]string{main}, fwd...)...)
	cmd.Dir, cmd.Env = root, env
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: createNoWindow}
	if err := cmd.Start(); err != nil {
		return false, err.Error()
	}
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()
	select {
	case err := <-done: // exited within a few seconds: fine if it handed over to a running copy (exit 0)
		if err != nil {
			return false, err.Error()
		}
		return true, ""
	case <-time.After(10 * time.Second):
		return true, ""
	}
}

func main() {
	exe, err := os.Executable()
	if err != nil {
		messageBox("Cannot find the program folder.", mbOK|mbIconError)
		return
	}
	if p, e := filepath.EvalSymlinks(exe); e == nil {
		exe = p
	}
	root := filepath.Dir(exe)

	repair, debug := false, shiftHeld()
	var fwd []string
	for _, a := range os.Args[1:] {
		switch strings.ToLower(a) {
		case "--repair", "--setup", "/repair":
			repair = true
		case "--debug", "/debug":
			debug = true
		default:
			fwd = append(fwd, a)
		}
	}

	// only one launcher at a time (double clicks)
	name, _ := syscall.UTF16PtrFromString("Local\\AudioTranscriber.Launcher")
	h, _, lastErr := procCreateMutexW.Call(0, 0, uintptr(unsafe.Pointer(name)))
	if h != 0 && lastErr == syscall.ERROR_ALREADY_EXISTS {
		return
	}

	if repair {
		openRepair(root)
		return
	}

	if !exists(filepath.Join(root, "app", "main.py")) {
		messageBox("The \"app\" folder is missing next to AudioTranscriber.exe.\n\nRun AudioTranscriber_Setup.exe again and choose Repair.", mbOK|mbIconError)
		return
	}
	// leftovers from the old portable version
	if bats, _ := filepath.Glob(filepath.Join(root, "*.bat")); len(bats) > 0 {
		for _, b := range bats {
			os.Remove(b)
		}
	}
	os.Remove(filepath.Join(root, "setup.ps1"))

	if m := missing(root); len(m) > 0 {
		msg := "AudioTranscriber isn't fully set up yet (the setup didn't run or didn't finish).\n\nMissing:\n  " +
			strings.Join(m, "\n  ") + "\n\nOpen Repair now? It downloads only what is missing."
		if messageBox(msg, mbYesNo|mbIconQuestion) == idYes {
			openRepair(root)
		}
		return
	}

	ok, why := launch(root, exe, fwd, debug)
	if ok {
		return
	}
	msg := "AudioTranscriber closed while starting"
	if why != "" {
		msg += " (" + why + ")"
	}
	msg += "."
	if t := logTail(root, 12); t != "" {
		msg += "\n\nLast lines of audiotranscriber.log:\n" + t
	}
	msg += "\n\nOpen Repair now? It checks every component and downloads only what is missing."
	if messageBox(msg, mbYesNo|mbIconWarning) == idYes {
		openRepair(root)
	}
}
