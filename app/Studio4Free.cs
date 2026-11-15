// Opens the Studio4Free page in its own window. The page's login is the owner's Claude account.
// Build: see build.cmd in this folder.
using System;
using System.Diagnostics;
using System.IO;

static class App
{
    const string Url = "https://claude.ai/artifact/YMfzPtdq6gnkGaHgLxUZPT";

    static void Main()
    {
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] roots = { Environment.GetEnvironmentVariable("ProgramFiles"), Environment.GetEnvironmentVariable("ProgramFiles(x86)"), local };
        string[] browsers = { @"Google\Chrome\Application\chrome.exe", @"Microsoft\Edge\Application\msedge.exe" };
        foreach (string b in browsers)
            foreach (string r in roots)
                if (r != null && File.Exists(Path.Combine(r, b)))
                {
                    Process.Start(Path.Combine(r, b), "--app=" + Url);
                    return;
                }
        Process.Start(Url);  // no Chrome or Edge found: the default browser opens the page in a tab
    }
}
