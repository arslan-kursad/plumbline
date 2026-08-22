using Plumbline.Normalization;
using Plumbline.Worker;
using Plumbline.Worker.Push;
using Plumbline.Worker.Sinks;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton(Normalizer.Default);
builder.Services.AddSingleton(WorkerOptions.FromConfiguration(builder.Configuration, builder.Environment));
builder.Services.AddSingleton(services => services.GetRequiredService<WorkerOptions>()
    .CreateAuthenticator(services.GetRequiredService<ILoggerFactory>()));
builder.Services.AddSingleton(services => services.GetRequiredService<WorkerOptions>().CreateSink());
builder.Services.AddSingleton<IngestionEndpoint>();

var app = builder.Build();

var options = app.Services.GetRequiredService<WorkerOptions>();
var authenticator = app.Services.GetRequiredService<IPushAuthenticator>();
var sink = app.Services.GetRequiredService<ISpanSink>();

app.Logger.LogInformation("ingestion worker starting: push authentication = {Auth}, sink = {Sink}",
    authenticator.Description, sink.Description);

if (authenticator is AcceptAllPushAuthenticator)
{
    // Loud on purpose. An endpoint whose only protection is the caller's identity,
    // running with that check off, is a fact that has to be visible from outside the
    // process — not a comment in a file someone would have to open.
    app.Logger.LogWarning("push authentication is off: every request to the push endpoint is accepted. "
                          + "Local development only — the cloud runs OIDC push validation (architecture §6.1).");
}

app.MapGet("/healthz", () => Results.Json(new
{
    status = "ok",
    push_authentication = authenticator.Description,
    sink = sink.Description,
}));

app.MapPost(options.PushPath, (HttpContext context, IngestionEndpoint endpoint, CancellationToken cancellationToken) =>
    endpoint.HandleAsync(context, cancellationToken));

app.Run();

/// <summary>Exposed so the test host can drive the same pipeline the deployment runs.</summary>
public partial class Program;
