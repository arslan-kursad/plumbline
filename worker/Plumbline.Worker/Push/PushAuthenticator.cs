using Google.Apis.Auth;

namespace Plumbline.Worker.Push;

/// <summary>Whether a push request really came from the Pub/Sub push subscription.</summary>
public interface IPushAuthenticator
{
    /// <summary>Name of the mechanism, for the startup log and the health endpoint.</summary>
    string Description { get; }

    /// <summary>True when the request is authenticated.</summary>
    ValueTask<bool> IsAuthenticAsync(HttpRequest request);
}

/// <summary>
/// OIDC push validation (architecture §6.1): the push subscription attaches a
/// Google-signed identity token, and this is the check that the token is genuine, meant
/// for this service, and minted for the push service account.
/// </summary>
/// <remarks>
/// <para>
/// Three assertions, in order: the signature and expiry are Google's
/// (<see cref="GoogleJsonWebSignature.ValidateAsync(string, GoogleJsonWebSignature.ValidationSettings)"/>
/// checks them against Google's published certificates, along with the issuer); the
/// audience is the fixed value this deployment and its push subscription agreed on; and
/// the issuer-verified email is the push service account's. The last one is what makes
/// the check authentication rather than "a Google-signed token exists" — any principal
/// with a Google identity can mint a token carrying an arbitrary audience.
/// </para>
/// <para>
/// The audience is a fixed string rather than the service URL because the URL does not
/// exist until the service does: the subscription (Wave 3) and the service (Wave 2) are
/// applied in different waves, and a URL-shaped audience would make the earlier one
/// depend on the later one's output. Pub/Sub's `oidc_token.audience` field carries any
/// agreed value.
/// </para>
/// </remarks>
public sealed class OidcPushAuthenticator : IPushAuthenticator
{
    private readonly string audience;
    private readonly string serviceAccountEmail;
    private readonly ILogger log;
    private readonly Func<string, GoogleJsonWebSignature.ValidationSettings, Task<GoogleJsonWebSignature.Payload>> validate;

    public OidcPushAuthenticator(string audience, string serviceAccountEmail, ILogger<OidcPushAuthenticator> log)
        : this(audience, serviceAccountEmail, log, GoogleJsonWebSignature.ValidateAsync)
    {
    }

    /// <summary>Test seam: everything after "is this token Google-signed" is this class's own logic.</summary>
    internal OidcPushAuthenticator(string audience, string serviceAccountEmail, ILogger log,
        Func<string, GoogleJsonWebSignature.ValidationSettings, Task<GoogleJsonWebSignature.Payload>> validate)
    {
        this.audience = audience;
        this.serviceAccountEmail = serviceAccountEmail;
        this.log = log;
        this.validate = validate;
    }

    public string Description => $"oidc (audience \"{audience}\", caller {serviceAccountEmail})";

    public async ValueTask<bool> IsAuthenticAsync(HttpRequest request)
    {
        var header = request.Headers.Authorization.ToString();
        if (!header.StartsWith("Bearer ", StringComparison.Ordinal))
        {
            log.LogWarning("push request carries no bearer token");
            return false;
        }

        GoogleJsonWebSignature.Payload payload;
        try
        {
            payload = await validate(header["Bearer ".Length..].Trim(),
                new GoogleJsonWebSignature.ValidationSettings { Audience = new[] { audience } });
        }
        catch (InvalidJwtException error)
        {
            // The reason is loggable: it describes the token, not a secret. A token is
            // an attacker-supplied input here, and "why was it refused" is exactly what
            // debugging a silently undelivered subscription needs.
            log.LogWarning("push token refused: {Reason}", error.Message);
            return false;
        }

        if (payload.EmailVerified != true
            || !string.Equals(payload.Email, serviceAccountEmail, StringComparison.OrdinalIgnoreCase))
        {
            log.LogWarning("push token is Google-signed for this audience but not from the push service account "
                           + "(email {Email}, verified {Verified})", payload.Email, payload.EmailVerified);
            return false;
        }

        return true;
    }
}

/// <summary>
/// No authentication: every request is accepted. Exists for the local pipeline only,
/// where the Pub/Sub emulator delivers pushes and cannot mint Google-signed tokens.
/// </summary>
/// <remarks>
/// Selecting it outside a Development environment is a startup failure
/// (<see cref="WorkerOptions.CreateAuthenticator"/>), Cloud Run sets no
/// <c>ASPNETCORE_ENVIRONMENT</c> so the guard bites by default, and the mechanism is
/// named in the startup log and on the health endpoint. This is deliberate, guarded
/// configuration — unlike the F1 stub it replaces, which stood in for a validator that
/// did not exist yet and is gone from the tree, asserted by the invariant gates.
/// </remarks>
public sealed class AcceptAllPushAuthenticator : IPushAuthenticator
{
    public string Description => "none (no authentication; local development only)";

    public ValueTask<bool> IsAuthenticAsync(HttpRequest request) => ValueTask.FromResult(true);
}
