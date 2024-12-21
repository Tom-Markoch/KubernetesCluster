/*
  Copyright (C) 2024 Tomislav Markoc, unpublished work. All rights reserved.
  Title and version: KubernetesCluster, version 2.0

  This is an unpublished work registered with the U.S. Copyright Office. As
  per https://www.copyright.gov/comp3/chap1900/ch1900-publication.pdf and
  https://www.govinfo.gov/content/pkg/USCODE-2011-title17/pdf/USCODE-2011-title17-chap1-sec101.pdf,
  public performance or a public display of a work "does not of itself
  constitute publication." Therefore, you only have permission to view this
  work in your web browser.

  You do not do not have permission to make copies by downloading files,
  copy and paste texts, use git clone, clone, fork, or use any other means
  to make copies of this work.

  If you make a copy of this work, you must delete it immediately.

  You do not have permission to modify this work or create derivative work.

  You do not have permission to use this work for any Artificial Intelligence
  (AI) purposes, including and not limited to training AI models or
  generative AI.

  By hosting this work you accept this agreement.

  In the case of conflict this licensing agreement takes precedence over all
  other agreements.

  In the case any provision of this licensing agreement is invalid or
  unenforceable, any invalidity or unenforceability will affect only that
  provision.

  ---------------------------------------------------------------------------

  Copyright statutory damages are up to $150,000 for willful infringement.
  Other damages may be more.

  This work was created without AI assistance. Therefore, the copyright
  status is clear.

  For info about this work or demo, contact me at tmarkoc@hotmail.com.
*/

using System.Collections;
using System.Text;

namespace MiniServer
{
    public class Program
    {
        private static string HomePage(HttpRequest request)
        {
            using MemoryStream s = new(10000);
            using StreamWriter w = new(s);
            ConnectionInfo connectionInfo = request.HttpContext.Connection;
            w.WriteLine($"MiniServer");
            w.WriteLine($"----------------------------------------------------------------");
            w.WriteLine($"CONNECTION INFO:");
            w.WriteLine($"Connection Id:    {connectionInfo.Id}");
            w.WriteLine($"Trace Id:         {request.HttpContext.TraceIdentifier}");
            w.WriteLine($"Source IP:        {connectionInfo.RemoteIpAddress}");
            w.WriteLine($"Source Port:      {connectionInfo.RemotePort}");
            w.WriteLine($"Destination IP:   {connectionInfo.LocalIpAddress}");
            w.WriteLine($"Destination Port: {connectionInfo.LocalPort}");
            w.WriteLine($"----------------------------------------------------------------");
            w.WriteLine($"HTTP HEADERS:");
            foreach (var header in request.Headers)
                w.WriteLine($"{header.Key}: {header.Value}");
            w.WriteLine($"----------------------------------------------------------------");
            w.WriteLine($"ENVIRONMENT VARIABLES:");
            foreach (DictionaryEntry varible in Environment.GetEnvironmentVariables())
                w.WriteLine($"{varible.Key}: {varible.Value}");
            w.WriteLine($"----------------------------------------------------------------");
            w.WriteLine($"Copyright (C) 2024 T.M., unpublished work. All rights reserved.");
            w.Flush();
            return Encoding.ASCII.GetString(s.ToArray());
        }
        public static void Main(string[] args)
        {
            var builder = WebApplication.CreateBuilder(args);
            var app = builder.Build();
            app.MapGet("/", (HttpRequest request) => HomePage(request));
            app.Run();
        }
    }
}
