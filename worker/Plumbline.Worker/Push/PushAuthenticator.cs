using Microsoft.Extensions.Primitives;

namespace Plumbline.Worker.Push;

/// <summary>Whether a push request really came from the Pub/Sub push subscription.</summary>
public interface IPushAuthenticator
{
    /// <summary>Name of the mechanism, for the startup log and the health endpoint.</summary>
    string Description { get; }

    /// <summary>True when the request is authenticated.</summary>
    bool IsAuthentic(HttpRequest request);
}

/// <summary>
/// The local stand-in: it authenticates nothing.
/// </summary>
/// <remarks>
/// <para>
/// **This must never run in the cloud.** Architecture §6.1 requires OIDC push: the push
/// service account is the sole `roles/run.invoker` on the worker, and the token it
/// presents is what makes the endpoint safe to expose at all. Real validation is F2 work.
/// </para>
/// <para>
/// It is a named class behind an interface, and it announces itself in the startup log
/// and on the health endpoint, so "the stub is deployed" is visible from outside the
/// process rather than discoverable only by reading the code. `RequireRealAuthentication`
/// makes it a startup failure to select it outside a development environment — an
/// interface with two implementations and no guard is how the wrong one ships.
/// </para>
/// </remarks>
public sealed class StubPushAuthenticator : IPushAuthenticator
{
    public const string Warning =
        "PUSH AUTHENTICATION IS STUBBED: every request to this endpoint is accepted. " +
        "Local development only — architecture §6.1 requires OIDC push validation, which lands in F2.";

    public string Description => "stub (no authentication)";

    public bool IsAuthentic(HttpRequest request) => true;
}

/// <summary>
/// Rejects everything, and exists so that the absence of a real implementation cannot be
/// mistaken for the presence of one.
/// </summary>
/// <remarks>
/// Selected when the worker is configured for OIDC but the F2 implementation is not
/// present. Failing closed is the only safe default for an endpoint whose whole
/// protection is the caller's identity.
/// </remarks>
public sealed class UnimplementedOidcAuthenticator : IPushAuthenticator
{
    public string Description => "oidc (not implemented — every request is refused)";

    public bool IsAuthentic(HttpRequest request) => false;
}
